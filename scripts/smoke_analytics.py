"""Real YOLO/ByteTrack ROI and heatmap smoke with numerical reconciliation, not GT."""

import argparse
import csv
import io
import json
from pathlib import Path

import numpy as np

from scripts.smoke_counting import SOURCE_URL, download_example, prepare_clip
from vision.contracts import AnalyticsConfig, ProcessingConfig
from vision.pipeline.video import process_video, sha256_file, write_json

CONFIG_PATH = Path(__file__).resolve().parents[1] / "examples/analytics/zones.json"


def reconcile(output):
    def rows(name):
        return list(csv.DictReader(io.StringIO((output / name).read_text())))

    summary = json.loads((output / "summary.json").read_text())
    visits = rows("zone_visits.csv")
    occupancy = rows("zone_occupancy.csv")
    events = rows("zone_events.csv")
    index = rows("heatmap_index.csv")
    manifest = json.loads((output / "manifest.json").read_text())
    assert len(visits) == summary["zones"]["total_visits"]
    assert {r["run_id"] for r in visits + occupancy + events + index} == {manifest["run_id"]}
    for group in summary["zones"]["by_zone_class"]:
        selected = [
            v
            for v in visits
            if v["zone_id"] == group["zone_id"] and int(v["class_id"]) == group["class_id"]
        ]
        assert len(selected) == group["closed_visits"] == group["visits"]
        assert sum(int(v["observations"]) for v in selected) == group["presence_observations"]
        assert np.isclose(
            sum(float(v["observed_dwell_s"]) for v in selected), group["observed_dwell_s"]
        )
        assert (
            sum(
                int(r["observed_count"])
                for r in occupancy
                if r["zone_id"] == group["zone_id"] and int(r["class_id"]) == group["class_id"]
            )
            == group["presence_observations"]
        )
    totals = {class_id: 0 for class_id in summary["heatmap"]["class_observations"]}
    for item in index:
        with np.load(output / item["array_file"], allow_pickle=False) as arrays:
            assert int(arrays["raw"].sum()) == int(item["observations"])
            assert np.isclose(arrays["smoothed"].sum(), arrays["raw"].sum())
            totals[item["class_id"]] += int(arrays["raw"].sum())
        assert (output / item["preview_file"]).is_file()
    assert totals == summary["heatmap"]["class_observations"]
    # Cross-check heatmap totals against the separately streamed trajectory evidence.
    for class_id, total in totals.items():
        with (output / "trajectories.csv").open() as file:
            observed = sum(
                1
                for r in csv.DictReader(file)
                if r["class_id"] == class_id
                and 0 <= float(r["bottom_center_x"]) <= 1280
                and 0 <= float(r["bottom_center_y"]) <= 720
            )
        assert total == observed
    return {
        "validation_kind": "real_integration_reconciliation_not_ground_truth",
        "selected_frames": summary["selected_frames"],
        "zone_visits": len(visits),
        "zone_events": len(events),
        "heatmap_files": len(index),
        "class_observations": totals,
        "observed_dwell_s": sum(float(v["observed_dwell_s"]) for v in visits),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--source", type=Path)
    sources.add_argument("--download-example", action="store_true")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source = download_example(Path("data/vehicles.mp4")) if args.download_example else args.source
    args.output_dir.mkdir(parents=True, exist_ok=False)
    clip = args.output_dir / "source-fixture.mp4"
    prepare_clip(source, clip)
    config = AnalyticsConfig.model_validate_json(CONFIG_PATH.read_text())
    write_json(
        args.output_dir / "provenance.json",
        {
            "source_url": SOURCE_URL,
            "source_sha256": sha256_file(source),
            "derived_sha256": sha256_file(clip),
            "analytics_config_sha256": sha256_file(CONFIG_PATH),
            "transform": "first 150 frames; 3840x2160 to 1280x720; 25fps; H264",
            "ground_truth": None,
            "redistributed": False,
        },
    )
    process_video(
        clip,
        args.output_dir / "result",
        checkpoint=args.checkpoint,
        config=ProcessingConfig(
            video_id="analytics-pilot",
            detector_model_id="yolo11n-coco",
            tracker_config_id="bytetrack-default",
            analytics=config,
        ),
    )
    report = reconcile(args.output_dir / "result")
    write_json(args.output_dir / "smoke-report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
