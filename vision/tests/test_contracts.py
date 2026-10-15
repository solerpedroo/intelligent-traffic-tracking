"""Boundary tests protect temporal, numerical and reproducibility conventions."""

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from pydantic import ValidationError

from vision.configs import load_catalog
from vision.contracts import (
    CrossingEvent,
    Detection,
    FramePacket,
    ProcessingConfig,
    RunManifest,
    RunProgress,
    SoftwareVersion,
    Track,
    TrackObservation,
    ZoneEvent,
)


def make_manifest(**overrides):
    data = {
        "run_id": "run-1",
        "video_id": "video-1",
        "input_sha256": "a" * 64,
        "config": ProcessingConfig(video_id="video-1"),
        "started_at": datetime(2026, 10, 15, tzinfo=UTC),
        "git_commit": None,
        "git_dirty": True,
        "seed": None,
        "hardware": "test CPU",
        "software": (SoftwareVersion(name="python", version="3.12"),),
    }
    return RunManifest(**(data | overrides))


def test_detection_preserves_original_pixel_coordinates():
    detection = Detection(bbox_xyxy=(-2.5, 4.0, 120.0, 90.5), class_id=0, confidence=0.75)
    assert detection.bbox_xyxy == (-2.5, 4.0, 120.0, 90.5)
    # Clipping needs actual image dimensions; contracts do not silently clip.
    with pytest.raises(ValidationError, match="frozen"):
        detection.confidence = 0.5


@pytest.mark.parametrize(
    "box",
    [(0, 0, 0, 2), (5, 0, 2, 3), (0, 3, 2, 1), (0, 0, float("nan"), 2), (0, 0, 2, float("inf"))],
)
def test_invalid_boxes_are_rejected(box):
    with pytest.raises(ValidationError):
        Detection(bbox_xyxy=box, class_id=0, confidence=0.5)


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": -0.1},
        {"confidence": 1.1},
        {"class_id": -1},
        {"class_id": True},
        {"class_id": "1"},
        {"extra_field": 3},
    ],
)
def test_detection_rejects_invalid_and_unknown_fields(changes):
    data = {"bbox_xyxy": (0.0, 0.0, 2.0, 3.0), "class_id": 0, "confidence": 0.5}
    with pytest.raises(ValidationError):
        Detection(**(data | changes))


def test_frame_packet_keeps_original_timeline_and_borrowed_pixels():
    pixels = np.zeros((4, 6, 3), dtype=np.uint8)
    packet = FramePacket(120, 4.125, pixels, "pts")
    assert packet.pixels is pixels
    assert packet.frame_index == 120
    assert packet.timestamp_s == 4.125


@pytest.mark.parametrize(
    "pixels",
    [
        np.zeros((4, 6), dtype=np.uint8),
        np.zeros((4, 6, 4), dtype=np.uint8),
        np.zeros((0, 6, 3), dtype=np.uint8),
        np.zeros((4, 6, 3), dtype=np.float32),
        np.zeros((4, 6, 3), dtype=np.uint8)[:, ::2],
    ],
)
def test_invalid_frame_buffers_are_rejected(pixels):
    with pytest.raises(ValueError):
        FramePacket(0, 0.0, pixels)


@pytest.mark.parametrize(
    "index, timestamp, source",
    [
        (-1, 0.0, "pts"),
        (True, 0.0, "pts"),
        (0, -1.0, "pts"),
        (0, float("nan"), "pts"),
        (0, float("inf"), "pts"),
        (0, True, "pts"),
        (0, 0.0, "unknown"),
    ],
)
def test_invalid_frame_metadata_is_rejected(index, timestamp, source):
    with pytest.raises(ValueError):
        FramePacket(index, timestamp, np.zeros((2, 2, 3), dtype=np.uint8), source)


def test_track_and_events_have_run_scoped_identity_and_explicit_state():
    track = Track(
        track_id=7, bbox_xyxy=(0.0, 0.0, 2.0, 3.0), class_id=0, confidence=None, state="predicted"
    )
    observation = TrackObservation(
        run_id="run-1", video_id="video-1", frame_index=10, timestamp_s=0.4, track=track
    )
    data = dict(
        run_id="run-1", video_id="video-1", frame_index=10, timestamp_s=0.4, track_id=7, class_id=0
    )
    crossing = CrossingEvent(**data, line_id="entry", direction="A_TO_B")
    lost = ZoneEvent(**data, zone_id="junction", event_type="observation_lost")
    assert observation.track.state == "predicted"
    assert crossing.event_type == "line_crossing"
    assert lost.event_type != "zone_exit"
    with pytest.raises(ValidationError):
        CrossingEvent(**data, line_id="entry", direction="forward")


@pytest.mark.parametrize(
    "changes",
    [
        {"frame_stride": 2},
        {"frame_stride": True},
        {"start_s": -1.0},
        {"start_s": 3.0, "end_s": 3.0},
        {"end_s": float("nan")},
        {"tracker_config_id": "preset"},
        {"video_id": "../video"},
        {"schema_version": "2.0"},
    ],
)
def test_config_rejects_unsupported_sampling_intervals_and_ids(changes):
    with pytest.raises(ValidationError):
        ProcessingConfig(**({"video_id": "video-1"} | changes))


def test_manifest_round_trip_keeps_nulls_and_reproducibility_fields():
    manifest = make_manifest()
    serialized = manifest.model_dump_json()
    assert RunManifest.model_validate_json(serialized) == manifest
    assert json.loads(serialized)["git_commit"] is None
    assert manifest.config.detector_model_id is None


@pytest.mark.parametrize(
    "changes",
    [
        {"input_sha256": "invalid"},
        {"git_commit": "a" * 41},
        {"video_id": "other-video"},
        {"started_at": datetime(2026, 10, 15)},
        {"finished_at": datetime(2026, 10, 14, tzinfo=UTC)},
        {"software": (SoftwareVersion(name="python", version="3.12"),) * 2},
    ],
)
def test_manifest_rejects_inconsistent_snapshots(changes):
    with pytest.raises(ValidationError):
        make_manifest(**changes)


def test_manifest_accepts_finished_run():
    end = datetime(2026, 10, 15, tzinfo=UTC) + timedelta(seconds=5)
    assert make_manifest(finished_at=end).finished_at == end


@pytest.mark.parametrize(
    "changes",
    [
        {"processed_frames": -1},
        {"processed_frames": 3, "total_frames": 2},
        {"state": "failed"},
        {"state": "running", "error": "unexpected"},
        {"state": "completed", "processed_frames": 2, "total_frames": 3},
    ],
)
def test_progress_rejects_inconsistent_counts_and_errors(changes):
    with pytest.raises(ValidationError):
        RunProgress(**changes)


def test_progress_distinguishes_unknown_totals_and_failure():
    assert RunProgress(state="running", processed_frames=2).total_frames is None
    assert RunProgress(state="failed", error="decode failed").error == "decode failed"


def test_packaged_catalog_is_empty_and_does_not_claim_available_models():
    catalog = load_catalog()
    assert catalog.models == ()
    assert catalog.tracker_configs == ()


def test_core_imports_do_not_load_transport_or_model_libraries():
    code = """
import sys
from vision.contracts import Detection, FramePacket, RunManifest
from vision.configs import load_catalog
assert load_catalog().models == ()
for name in ('fastapi', 'backend', 'torch', 'ultralytics', 'cv2'):
    assert name not in sys.modules, name
"""
    subprocess.run([sys.executable, "-I", "-c", code], check=True)
