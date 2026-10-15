"""Explicit real CPU smoke using an image repeated in a short video, not a traffic benchmark."""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

import cv2

from vision.contracts import FramePacket, ProcessingConfig, RunManifest
from vision.pipeline.video import process_video, write_json
from vision.video import VideoWriter

EXAMPLE_URL = (
    "https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.177/ultralytics/assets/bus.jpg"
)
EXAMPLE_SHA256 = "c02019c4979c191eb739ddd944445ef408dad5679acab6fd520ef9d434bfbc63"
EXAMPLE_BYTES = 137419


def prepare_example(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urlopen(EXAMPLE_URL, timeout=30) as response:
            payload = response.read(EXAMPLE_BYTES + 1)
        if len(payload) != EXAMPLE_BYTES or hashlib.sha256(payload).hexdigest() != EXAMPLE_SHA256:
            raise ValueError("Official example size/hash differs from the pinned asset")
        with path.open("xb") as output:
            output.write(payload)
    if hashlib.sha256(path.read_bytes()).hexdigest() != EXAMPLE_SHA256:
        raise ValueError("Existing example differs; it will not be overwritten")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracker", choices=["bytetrack-default"])
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--image", type=Path)
    source.add_argument("--download-example", action="store_true")
    args = parser.parse_args()
    image_path = (
        prepare_example(Path("data/detector-smoke-bus.jpg"))
        if args.download_example
        else args.image
    )
    image = cv2.imread(str(image_path))
    if image is None:
        parser.error("Cannot decode the supplied image")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    source_video = args.output_dir / "source-fixture.mp4"
    with VideoWriter(source_video, image.shape[1], image.shape[0], 25.0) as writer:
        for index in range(4):
            writer.write(FramePacket(index, index / 25, image, duration_s=1 / 25))
    write_json(
        args.output_dir / "fixture-provenance.json",
        {
            "kind": "repeated_still_image_not_real_traffic_sequence",
            "source_url": EXAMPLE_URL if args.download_example else None,
            "source_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
            "frames": 4,
            "fps": 25,
            "ground_truth": None,
            "redistributed": False,
        },
    )
    output = args.output_dir / "result"
    result = process_video(
        source_video,
        output,
        checkpoint=args.checkpoint,
        config=ProcessingConfig(
            video_id="detector-smoke",
            detector_model_id="yolo11n-coco",
            tracker_config_id=args.tracker,
        ),
    )
    manifest = RunManifest.model_validate_json((output / "manifest.json").read_text())
    assert manifest.detector is not None and manifest.finished_at is not None
    assert result["selected_frames"] == 4
    if args.download_example:
        assert result["detector"]["class_observations"].get("bus", 0) > 0
    if args.tracker:
        import csv

        with (output / "trajectories.csv").open() as file:
            points = list(csv.DictReader(file))
        assert points, "Real YOLO + ByteTrack produced no confirmed tracks"
        first_ids = {p["track_id"] for p in points if p["frame_index"] == "0"}
        last_ids = {p["track_id"] for p in points if p["frame_index"] == "3"}
        assert first_ids & last_ids, "No ID persisted across the repeated still fixture"
        assert manifest.tracker is not None
    write_json(args.output_dir / "smoke-report.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
