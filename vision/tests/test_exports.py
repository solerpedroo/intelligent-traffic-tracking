"""Export integrity: schemas, empty tables, codec failure, and numeric survival."""

import csv
import json
from pathlib import Path

import pytest

from scripts.generate_sample import generate_sample
from vision.contracts import (
    AnalyticsConfig,
    CountingConfig,
    HeatmapConfig,
    LineConfig,
    ProcessingConfig,
    ZoneConfig,
)
from vision.detectors.base import DetectionBatch
from vision.pipeline.cli import main
from vision.pipeline.schemas import COLUMN_UNITS, EXPORT_SCHEMA_VERSION, EXPORT_TABLES
from vision.pipeline.video import process_video
from vision.tests.test_detection import FixtureDetector
from vision.video import VideoError, VideoWriter


def headers(path):
    return tuple(next(csv.reader(path.read_text().splitlines())))


def rows(path):
    return list(csv.DictReader(path.read_text().splitlines()))


def test_export_schema_version_and_units_are_explicit():
    assert EXPORT_SCHEMA_VERSION == "1.0"
    assert COLUMN_UNITS["timestamp_s"] == "seconds_on_original_media_timeline"
    assert COLUMN_UNITS["observed_dwell_s"] == "seconds_of_consecutive_inside_observations"
    assert COLUMN_UNITS["x1"] == "original_pixels"
    assert set(EXPORT_TABLES) >= {
        "frames.csv",
        "detections.csv",
        "tracks.csv",
        "crossing_events.csv",
        "zone_visits.csv",
        "heatmap_index.csv",
    }


def test_short_pipeline_reconciles_schema_config_and_empty_detections(tmp_path):
    source = tmp_path / "source.mp4"
    generate_sample(source, frames=4)

    class EmptyDetector(FixtureDetector):
        def detect(self, pixels):
            self.calls += 1
            return DetectionBatch((), 1.0, 1.0, 1.0, 1.0)

    config = ProcessingConfig(video_id="fixture", detector_model_id="yolo11n-coco")
    first = tmp_path / "first"
    summary = process_video(source, first, config=config, detector=EmptyDetector())
    assert summary["status"] == "completed"
    assert summary["numeric_results_valid"] is True
    assert summary["export"]["state"] == "published"
    assert summary["export"]["codec"] == "h264"
    assert summary["warnings"] == []
    assert summary["detector"]["total_box_observations"] == 0
    assert headers(first / "frames.csv") == EXPORT_TABLES["frames.csv"]
    assert headers(first / "detections.csv") == EXPORT_TABLES["detections.csv"]
    assert headers(first / "timings.csv") == EXPORT_TABLES["timings.csv"]
    assert rows(first / "detections.csv") == []
    saved = json.loads((first / "config.json").read_text())
    assert saved["export_schema_version"] == EXPORT_SCHEMA_VERSION
    assert saved["processing"] == config.model_dump(mode="json")
    manifest = json.loads((first / "manifest.json").read_text())
    assert manifest["schema_version"] == "1.0"
    assert manifest["config"] == saved["processing"]

    second = tmp_path / "second"
    replayed = ProcessingConfig.model_validate_json(json.dumps(saved["processing"]))
    again = process_video(source, second, config=replayed, detector=EmptyDetector())
    assert again["selected_frames"] == summary["selected_frames"]
    assert (second / "frames.csv").read_text() == (first / "frames.csv").read_text()
    assert json.loads((second / "manifest.json").read_text())["run_id"] != manifest["run_id"]
    assert not (first / "failure.json").exists()
    assert not list(first.glob("*.partial"))


def test_skipped_annotated_video_keeps_numeric_exports(sample, tmp_path):
    output = tmp_path / "numeric"
    summary = process_video(
        sample,
        output,
        config=ProcessingConfig(video_id="plain", render_annotated_video=False),
    )
    assert summary["status"] == "completed_with_warnings"
    assert summary["numeric_results_valid"] is True
    assert summary["export"]["state"] == "skipped"
    assert summary["warnings"][0]["code"] == "annotated_video_skipped"
    assert (output / "frames.csv").is_file()
    assert (output / "summary.json").is_file()
    assert (output / "manifest.json").is_file()
    assert (output / "preview.png").is_file()
    assert not (output / "video.mp4").exists()
    assert not (output / "video.mp4.partial").exists()
    assert len(rows(output / "frames.csv")) == 12


def test_cli_can_skip_annotated_video(sample, tmp_path, capsys):
    output = tmp_path / "cli"
    assert (
        main(
            [
                "process",
                str(sample),
                "--output-dir",
                str(output),
                "--no-annotated-video",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["export"]["state"] == "skipped"
    assert (output / "frames.csv").is_file()
    assert not (output / "video.mp4").exists()


def test_codec_failure_preserves_numeric_results(sample, tmp_path, monkeypatch):
    def fail(self, packet):
        raise VideoError("encode_error", "injected encoder failure")

    monkeypatch.setattr(VideoWriter, "write", fail)
    output = tmp_path / "codec"
    summary = process_video(sample, output, config=ProcessingConfig(video_id="codec"))
    assert summary["status"] == "completed_with_warnings"
    assert summary["numeric_results_valid"] is True
    assert summary["export"]["state"] == "failed"
    assert summary["warnings"][0]["code"] == "encode_error"
    assert summary["selected_frames"] == 12
    assert not (output / "video.mp4").exists()
    assert len(rows(output / "frames.csv")) == 12
    assert not (output / "failure.json").exists()


def test_interrupted_table_write_does_not_publish_summary(sample, tmp_path, monkeypatch):
    original = Path.open

    def flaky(self, *args, **kwargs):
        handle = original(self, *args, **kwargs)
        if not str(self).endswith("frames.csv.partial"):
            return handle

        class Proxy:
            def __init__(self):
                self._header = False

            def write(self, data):
                if self._header:
                    raise OSError("injected write failure")
                self._header = True
                return handle.write(data)

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return handle.__exit__(exc_type, exc, traceback)

            def __getattr__(self, name):
                return getattr(handle, name)

        return Proxy()

    monkeypatch.setattr(Path, "open", flaky)
    output = tmp_path / "interrupted"
    with pytest.raises(OSError, match="injected write failure"):
        process_video(sample, output, config=ProcessingConfig(video_id="broken"))
    report = json.loads((output / "failure.json").read_text())
    assert report["final_artifacts_valid"] is False
    assert report["status"] == "failed"
    assert not (output / "summary.json").exists()
    assert not (output / "frames.csv").exists()
    assert (output / "frames.csv.partial").is_file()


@pytest.mark.tracker
def test_full_pipeline_numbers_survive_without_annotated_video(tmp_path):
    source = tmp_path / "source.mp4"
    generate_sample(source, frames=5)
    config = ProcessingConfig(
        video_id="v",
        detector_model_id="yolo11n-coco",
        tracker_config_id="bytetrack-default",
        render_annotated_video=False,
        counting=CountingConfig(
            lines=(LineConfig(line_id="gate", start=(0.0, 0.5), end=(1.0, 0.5)),)
        ),
        analytics=AnalyticsConfig(
            zones=(
                ZoneConfig(
                    zone_id="all", vertices=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
                ),
            ),
            heatmap=HeatmapConfig(
                enabled=True, class_ids=(5,), grid_width=8, grid_height=8, window_s=1.0
            ),
        ),
    )
    output = tmp_path / "numeric"
    summary = process_video(source, output, config=config, detector=FixtureDetector())
    visits = rows(output / "zone_visits.csv")
    events = rows(output / "crossing_events.csv")
    index = rows(output / "heatmap_index.csv")
    assert summary["status"] == "completed_with_warnings"
    assert summary["export"]["state"] == "skipped"
    assert summary["numeric_results_valid"] is True
    assert len(visits) == summary["zones"]["total_visits"] == 1
    assert len(events) == summary["counting"]["total_events"] == 0
    assert index[0]["observations"] == "5"
    assert summary["heatmap"]["class_observations"] == {"5": 5}
    assert headers(output / "zone_visits.csv") == EXPORT_TABLES["zone_visits.csv"]
    assert headers(output / "crossing_events.csv") == EXPORT_TABLES["crossing_events.csv"]
    assert headers(output / "tracks.csv") == EXPORT_TABLES["tracks.csv"]
    assert not (output / "video.mp4").exists()
    assert not list(output.glob("*.partial"))


@pytest.fixture
def sample(tmp_path):
    path = tmp_path / "sample.mp4"
    generate_sample(path, frames=12)
    return path
