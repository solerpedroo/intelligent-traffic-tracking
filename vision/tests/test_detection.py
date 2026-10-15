"""Lightweight checks: geometry, validation, visualization and pipeline contracts."""

import csv
import io
import json

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.generate_sample import generate_sample
from vision.configs import load_catalog
from vision.contracts import Detection, ProcessingConfig, RunManifest
from vision.contracts.config import DetectorConfig
from vision.contracts.errors import VisionError
from vision.contracts.run import ModelReference
from vision.detectors.base import DetectionBatch
from vision.detectors.checkpoint import prepare_checkpoint, verify_checkpoint
from vision.detectors.geometry import LetterboxTransform
from vision.detectors.yolo import normalize_detections
from vision.pipeline.video import process_video
from vision.rendering.detections import render_detections


@pytest.mark.parametrize("height,width", [(720, 1280), (1080, 810), (321, 777), (640, 640)])
def test_letterbox_known_box_round_trip_and_padding(height, width):
    transform = LetterboxTransform.for_shape(height, width, 640)
    pixels = np.full((height, width, 3), (10, 20, 30), dtype=np.uint8)
    source = pixels.copy()
    canvas = transform.apply(pixels)
    assert canvas.shape == (640, 640, 3)
    np.testing.assert_array_equal(pixels, source)
    boxes = np.array(
        [[0, 0, width, height], [width / 4, height / 4, width / 2, height / 2]], dtype=float
    )
    projected = boxes.copy()
    projected[:, (0, 2)] = boxes[:, (0, 2)] * (transform.resized_width / width) + transform.left
    projected[:, (1, 3)] = boxes[:, (1, 3)] * (transform.resized_height / height) + transform.top
    np.testing.assert_allclose(transform.restore_boxes(projected), boxes, atol=1e-10)
    if transform.top:
        np.testing.assert_array_equal(canvas[0, 0], [114, 114, 114])


def test_normalization_clips_padding_and_accepts_empty_predictions():
    transform = LetterboxTransform.for_shape(100, 200, 640)
    result = normalize_detections(
        [[0, 0, 640, 640], [0, 0, 10, 10]], [0.9, 0.3], [2, 2], transform, {2}
    )
    assert len(result) == 1
    assert result[0].bbox_xyxy == (0, 0, 200, 100)
    assert normalize_detections(np.empty((0, 4)), [], [], transform, {2}) == ()


@pytest.mark.parametrize(
    "boxes,scores,classes",
    [
        ([[0, 0, float("nan"), 20]], [0.5], [2]),
        ([[0, 0, 20, 20]], [1.1], [2]),
        ([[0, 0, 20, 20]], [0.5], [99]),
        ([[0, 0, 20, 20]], [0.5], [2.5]),
        ([[0, 0, 20, 20]], [], [2]),
    ],
)
def test_invalid_predictions_are_not_silently_exported(boxes, scores, classes):
    with pytest.raises(VisionError):
        normalize_detections(
            boxes, scores, classes, LetterboxTransform.for_shape(100, 100, 640), {2}
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": -0.1},
        {"confidence": float("nan")},
        {"iou": 1.1},
        {"image_size": 321},
        {"image_size": 160},
        {"classes": ()},
        {"classes": ("car", "car")},
        {"device": "auto"},
        {"warmup_frames": 0},
        {"threads": 0},
        {"seed": -1},
    ],
)
def test_detector_configuration_rejects_invalid_controls(changes):
    with pytest.raises(ValidationError):
        DetectorConfig(**changes)


def test_model_classes_are_resolved_against_real_coco_mapping():
    model = load_catalog().get_model("yolo11n-coco")
    assert model.resolve_classes(DetectorConfig().classes) == (0, 1, 2, 3, 5, 7)
    with pytest.raises(VisionError, match="Unsupported model classes"):
        model.resolve_classes(("van",))
    assert load_catalog().detector_defaults == DetectorConfig()


def test_rendering_does_not_remove_weak_detections_or_mutate_input():
    pixels = np.zeros((100, 200, 3), dtype=np.uint8)
    detections = (
        Detection(bbox_xyxy=(10.0, 10.0, 50.0, 50.0), class_id=2, confidence=0.15),
        Detection(bbox_xyxy=(60.0, 10.0, 100.0, 50.0), class_id=5, confidence=0.9),
    )
    rendered, count = render_detections(pixels, detections, {2: "car", 5: "bus"}, 0.25)
    assert count == 1
    assert len(detections) == 2
    assert not pixels.any() and rendered.any()


def test_wrong_checkpoint_is_rejected_before_framework_import(tmp_path):
    path = tmp_path / "wrong.pt"
    path.write_bytes(b"not a checkpoint")
    with pytest.raises(VisionError, match="SHA-256"):
        verify_checkpoint(path, load_catalog().get_model("yolo11n-coco"))


def test_prepare_does_not_replace_existing_wrong_weights_or_partial(tmp_path):
    model = load_catalog().get_model("yolo11n-coco")
    target = tmp_path / model.filename
    target.write_bytes(b"keep")
    with pytest.raises(VisionError):
        prepare_checkpoint(model, tmp_path)
    assert target.read_bytes() == b"keep"


def test_prepare_verifies_download_and_publishes_without_overwrite(tmp_path, monkeypatch):
    import hashlib

    from vision.detectors import checkpoint

    payload = b"test fixture, not model weights"
    model = (
        load_catalog()
        .get_model("yolo11n-coco")
        .model_copy(
            update={
                "size_bytes": len(payload),
                "checkpoint_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    )
    monkeypatch.setattr(checkpoint, "urlopen", lambda *a, **k: io.BytesIO(payload))
    path = prepare_checkpoint(model, tmp_path)
    assert path.read_bytes() == payload
    assert not list(tmp_path.glob("*.partial"))


class FixtureDetector:
    load_ms = 1.0
    warmup_ms = 2.0

    def __init__(self):
        model = load_catalog().get_model("yolo11n-coco")
        self.reference = ModelReference(
            model_id=model.model_id,
            checkpoint_sha256=model.checkpoint_sha256,
            implementation_version=model.implementation_version,
        )
        self.class_names = {c.id: c.name for c in model.classes}
        self.calls = 0
        self.warmups = 0

    def warm_up(self, pixels):
        self.warmups += 1

    def detect(self, pixels):
        self.calls += 1
        return DetectionBatch(
            (
                Detection(bbox_xyxy=(10.0, 10.0, 50.0, 50.0), class_id=2, confidence=0.15),
                Detection(bbox_xyxy=(60.0, 10.0, 100.0, 50.0), class_id=5, confidence=0.9),
            ),
            1.0,
            3.0,
            0.5,
            2.0,
        )


def test_pipeline_exports_observations_manifest_and_separate_timings(tmp_path):
    path = tmp_path / "sample.mp4"
    generate_sample(path, frames=4)
    adapter = FixtureDetector()
    output = tmp_path / "output"
    config = ProcessingConfig(video_id="fixture", detector_model_id="yolo11n-coco")
    result = process_video(path, output, config=config, detector=adapter)
    rows = list(csv.DictReader((output / "detections.csv").read_text().splitlines()))
    times = list(csv.DictReader((output / "timings.csv").read_text().splitlines()))
    assert len(rows) == 8 and len(times) == 4
    assert adapter.calls == 4 and adapter.warmups == 1
    assert result["detector"]["boxes_rendered"] == 4
    assert result["detector"]["class_observations"] == {"car": 4, "bus": 4}
    assert result["inference_fps"] == 500
    manifest = RunManifest.model_validate_json((output / "manifest.json").read_text())
    assert manifest.finished_at is not None and manifest.detector.model_id == "yolo11n-coco"
    assert manifest.config.detector.confidence == 0.1
    assert {r["run_id"] for r in rows} == {manifest.run_id}
    assert float(times[0]["inference_ms"]) == 2
    assert json.loads((output / "summary.json").read_text())["status"] == "completed"


def test_pipeline_rejects_missing_checkpoint_before_output(tmp_path):
    with pytest.raises(VisionError, match="verified local checkpoint"):
        process_video(
            tmp_path / "missing.mp4",
            tmp_path / "output",
            config=ProcessingConfig(video_id="test", detector_model_id="yolo11n-coco"),
        )
    assert not (tmp_path / "output").exists()


def test_prepare_preserves_a_partial_created_by_another_process(tmp_path):
    model = load_catalog().get_model("yolo11n-coco")
    partial = tmp_path / (model.filename + ".partial")
    partial.write_bytes(b"existing work")
    with pytest.raises(FileExistsError):
        prepare_checkpoint(model, tmp_path)
    assert partial.read_bytes() == b"existing work"


def test_missing_detector_distribution_has_actionable_error(tmp_path, monkeypatch):
    import hashlib
    from importlib.metadata import PackageNotFoundError

    from vision.detectors import yolo

    payload = b"fixture not executable model"
    path = tmp_path / "fixture.pt"
    path.write_bytes(payload)
    model = (
        load_catalog()
        .get_model("yolo11n-coco")
        .model_copy(
            update={
                "size_bytes": len(payload),
                "checkpoint_sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    )

    def missing(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(yolo, "version", missing)
    with pytest.raises(VisionError) as raised:
        yolo.UltralyticsDetector(model, path, DetectorConfig())
    assert raised.value.code == "missing_detector_extra"
