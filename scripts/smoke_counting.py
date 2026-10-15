"""Explicit real traffic development smoke; no formal benchmark or MOT metrics."""

import argparse
import csv
import json
from pathlib import Path
from urllib.request import urlopen

import av

from vision.contracts import CountingConfig, FramePacket, ProcessingConfig
from vision.pipeline.video import process_video, sha256_file, write_json
from vision.video import VideoWriter

EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "counting"
SOURCE_URL = "https://media.roboflow.com/supervision/video-examples/vehicles.mp4"
SOURCE_SHA256 = "ac81100d9310bd4e9c02bc0b13b6492781d009742ced347766b2601be3c44ad4"
SOURCE_MAX_BYTES = 40 * 1024 * 1024


def download_example(path):
    """Download only on explicit request; never replace an existing source."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with urlopen(SOURCE_URL, timeout=30) as response:
            payload = response.read(SOURCE_MAX_BYTES + 1)
        import hashlib

        if len(payload) > SOURCE_MAX_BYTES or hashlib.sha256(payload).hexdigest() != SOURCE_SHA256:
            raise ValueError("Example differs from pinned source")
        with path.open("xb") as file:
            file.write(payload)
    return path


def prepare_clip(source, output):
    """Derive the documented first 150 frames at 1280x720; preserve their CFR cadence."""
    if sha256_file(source) != SOURCE_SHA256:
        raise ValueError("Source differs from the annotated example")
    count = 0
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        if (stream.width, stream.height, stream.average_rate) != (3840, 2160, 25):
            raise ValueError("Source geometry/cadence changed")
        with VideoWriter(output, 1280, 720, 25.0) as writer:
            for index, item in enumerate(container.decode(video=0)):
                if index == 150:
                    break
                if item.pts is None or abs(float(item.pts * item.time_base) - index / 25) > 1e-6:
                    raise ValueError("Source PTS differ from annotated fixture")
                pixels = item.reformat(width=1280, height=720, format="bgr24").to_ndarray()
                writer.write(FramePacket(index, index / 25, pixels, duration_s=1 / 25))
                count += 1
    if count != 150:
        raise ValueError("Source has insufficient frames")


def compare_annotations(events, annotation):
    """One-to-one sanity matching in the small explicit annotation intervals."""
    remaining = list(events)
    missing = []
    matched = []
    for expected in annotation["events"]:
        low, high = expected["crossing_frame_interval"]
        match = next(
            (
                event
                for event in remaining
                if all(
                    str(event[key]) == str(expected[key])
                    for key in ("line_id", "class_id", "direction")
                )
                and low
                <= int(event["frame_index"])
                <= high + annotation["confirmation_tolerance_frames"]
            ),
            None,
        )
        if match is None:
            missing.append(expected)
        else:
            remaining.remove(match)
            matched.append({"object_note": expected["object_note"], "event": match})
    return {
        "expected_events": len(annotation["events"]),
        "observed_events": len(events),
        "matched": matched,
        "missing": missing,
        "unexpected": remaining,
        "validation_kind": annotation["purpose"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source", type=Path)
    source.add_argument("--download-example", action="store_true")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source_path = (
        download_example(Path("data/vehicles.mp4")) if args.download_example else args.source
    )
    args.output_dir.mkdir(parents=True, exist_ok=False)
    clip = args.output_dir / "source-fixture.mp4"
    prepare_clip(source_path, clip)
    annotation = json.loads((EXAMPLES / "manual-events.json").read_text())
    counting = CountingConfig.model_validate_json((EXAMPLES / "lines.json").read_text())
    write_json(
        args.output_dir / "provenance.json",
        {
            "source_url": SOURCE_URL,
            "source_sha256": sha256_file(source_path),
            "derived_sha256": sha256_file(clip),
            "transform": annotation["derived_input"],
            "annotation_sha256": sha256_file(EXAMPLES / "manual-events.json"),
            "counting_config_sha256": sha256_file(EXAMPLES / "lines.json"),
            "redistributed": False,
        },
    )
    result = process_video(
        clip,
        args.output_dir / "result",
        checkpoint=args.checkpoint,
        config=ProcessingConfig(
            video_id="counting-pilot",
            detector_model_id="yolo11n-coco",
            tracker_config_id="bytetrack-default",
            counting=counting,
        ),
    )
    with (args.output_dir / "result" / "crossing_events.csv").open() as file:
        events = list(csv.DictReader(file))
    comparison = compare_annotations(events, annotation)
    assert result["counting"]["total_events"] == len(events)
    write_json(args.output_dir / "comparison.json", comparison)
    print(json.dumps(comparison, indent=2))
    if comparison["missing"] or comparison["unexpected"]:
        raise SystemExit("Manual development comparison has divergences; see comparison.json")


if __name__ == "__main__":
    main()
