"""Real ByteTrack controlled sequences; these do not estimate MOT performance."""

import csv
import io
import json
from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.generate_sample import generate_sample
from vision.contracts import Detection, FramePacket, ProcessingConfig, RunManifest, Track
from vision.contracts.config import DetectorConfig, TrackerConfig
from vision.contracts.errors import VisionError
from vision.pipeline.video import process_video
from vision.tests.test_detection import FixtureDetector
from vision.trackers.history import TrackHistoryManager


@pytest.fixture(autouse=True)
def no_tracker_network(request, monkeypatch):
    if request.node.get_closest_marker("tracker"):
        import socket

        def denied(*args, **kwargs):
            raise AssertionError("Tracking must never initiate network access")

        monkeypatch.setattr(socket.socket, "connect", denied)


def frame(index, timestamp=None):
    return FramePacket(
        index,
        float(index / 25 if timestamp is None else timestamp),
        np.zeros((100, 200, 3), dtype=np.uint8),
    )


def detection(x=10.0, confidence=0.9, class_id=2):
    return Detection(bbox_xyxy=(x, 10.0, x + 40, 50.0), class_id=class_id, confidence=confidence)


def tracker(**options):
    from vision.trackers.bytetrack import ByteTrackAdapter

    return ByteTrackAdapter(TrackerConfig(**options))


@pytest.mark.parametrize(
    "options",
    [
        {"track_low_thresh": 0.3},
        {"new_track_thresh": 0.2},
        {"track_buffer": 0},
        {"history_points": 1},
        {"match_thresh": float("nan")},
        {"max_live_tracks": 0},
    ],
)
def test_invalid_tracker_controls(options):
    with pytest.raises(ValidationError):
        TrackerConfig(**options)


def test_detector_must_preserve_low_confidence_band():
    with pytest.raises(ValidationError, match="confidence"):
        ProcessingConfig(
            video_id="v",
            detector_model_id="yolo11n-coco",
            tracker_config_id="bytetrack-default",
            detector=DetectorConfig(confidence=0.2),
        )


@pytest.mark.tracker
def test_real_two_stage_association_and_class_stability():
    adapter = tracker()
    first = adapter.update(frame(0), (detection(),))[0]
    second = adapter.update(frame(1), (detection(12.0, 0.15, 5),))[0]
    assert first.track_id == second.track_id == 1
    assert second.class_id == 2 and second.confidence == 0.15
    assert second.bbox_xyxy == (12, 10, 52, 50)
    assert second.state == "observed"
    # Low scores recover existing tracks; they cannot create new identities.
    assert adapter.update(frame(2), (detection(140.0, 0.15),))[0].state == "lost"
    assert tracker().update(frame(0), (detection(confidence=0.15),)) == ()


@pytest.mark.tracker
def test_short_occlusion_empty_frames_and_reactivation():
    adapter = tracker(track_buffer=3)
    assert adapter.update(frame(10, 1.0), (detection(),))[0].track_id == 1
    lost = adapter.update(frame(11, 20.0), ())[0]
    assert lost.state == "lost" and lost.confidence is None
    # Buffer is frames, even when PTS gap is large (VFR).
    assert adapter.update(frame(12, 40.0), (detection(),))[0].track_id == 1


@pytest.mark.tracker
def test_buffer_boundary_cannot_revive_expired_id():
    adapter = tracker(track_buffer=2)
    adapter.update(frame(0), (detection(),))
    adapter.update(frame(1), ())
    assert adapter.update(frame(2), (detection(),))[0].track_id == 1
    adapter.update(frame(3), ())
    adapter.update(frame(4), ())
    assert adapter.update(frame(5), (detection(),)) == ()  # new track pending confirmation
    assert adapter.update(frame(6), (detection(),))[0].track_id == 2


@pytest.mark.tracker
def test_reset_and_interleaved_instances_have_independent_ids():
    one, two = tracker(), tracker()
    assert one.update(frame(0), (detection(),))[0].track_id == 1
    assert two.update(frame(0), (detection(),))[0].track_id == 1
    assert one.update(frame(1), (detection(), detection(140.0)))[0].track_id == 1
    assert [t.track_id for t in one.update(frame(2), (detection(), detection(140.0)))] == [1, 2]
    two.reset()
    assert two.update(frame(100, 10.0), (detection(),))[0].track_id == 1
    assert [t.track_id for t in one.update(frame(3), (detection(), detection(140.0)))] == [1, 2]
    one.reset()
    assert one.update(frame(0), ()) == ()
    assert one._classes == {}


@pytest.mark.tracker
@pytest.mark.parametrize("bad", [frame(2), frame(1, 0.0)])
def test_order_contract(bad):
    adapter = tracker()
    adapter.update(frame(0), ())
    with pytest.raises(VisionError, match="consecutive"):
        adapter.update(bad, ())


@pytest.mark.tracker
def test_live_limit_fails_explicitly():
    with pytest.raises(VisionError, match="limit"):
        tracker(max_live_tracks=1).update(frame(0), (detection(), detection(140.0)))


@pytest.mark.tracker
def test_long_sequence_keeps_tracker_metadata_bounded():
    adapter = tracker(track_buffer=2)
    for index in range(4404):
        adapter.update(frame(index), (detection(),) if index % 4 == 0 else ())
        assert len(adapter._classes) <= 1
        assert len(adapter._tracker.lost_stracks) <= 1
        assert len(adapter._tracker.removed_stracks) <= 1000
    assert len(adapter._tracker.removed_stracks) == 1000


def test_history_streams_every_observation_but_bounds_memory_and_censors_end():
    trajectories, lifetimes = io.StringIO(), io.StringIO()
    history = TrackHistoryManager(
        "run", "video", 3, csv.writer(trajectories), csv.writer(lifetimes)
    )
    observed = Track(track_id=1, class_id=2, confidence=0.15, bbox_xyxy=(10.0, 10.0, 50.0, 50.0))
    for index in range(100):
        history.update(frame(index), (observed,))
    assert len(history.histories[1].points) == 3
    history.update(frame(100), (observed.model_copy(update={"state": "lost", "confidence": None}),))
    assert history.total_observations == 100
    history.update(frame(101), ())
    assert history.histories == {}
    history.update(frame(102), (observed.model_copy(update={"track_id": 2}),))
    history.finish()
    assert history.histories == {} and history.total_tracks == 2
    rows = list(csv.reader(io.StringIO(trajectories.getvalue())))
    assert len(rows) == 101 and rows[0][-2:] == ["30.0", "50.0"]
    closed = list(csv.reader(io.StringIO(lifetimes.getvalue())))
    assert closed[0][-2] == "removed" and closed[0][-3] == "100" and closed[0][-1] == "True"
    assert closed[1][-2] == "selection_end_censored" and closed[1][-1] == "False"


@pytest.mark.tracker
def test_tracking_pipeline_exports_and_resets_for_second_run(tmp_path):
    source = tmp_path / "source.mp4"
    generate_sample(source, profile="vfr", frames=4)
    config = ProcessingConfig(
        video_id="test", detector_model_id="yolo11n-coco", tracker_config_id="bytetrack-default"
    )
    for run in ("first", "second"):
        output = tmp_path / run
        summary = process_video(source, output, config=config, detector=FixtureDetector())
        manifest = RunManifest.model_validate_json((output / "manifest.json").read_text())
        assert manifest.tracker.implementation_version == "8.4.177"
        assert manifest.config.tracker == TrackerConfig()
        assert manifest.finished_at is not None
        tracks = list(csv.DictReader(io.StringIO((output / "tracks.csv").read_text())))
        points = list(csv.DictReader(io.StringIO((output / "trajectories.csv").read_text())))
        assert len(points) == summary["selected_frames"]
        assert {row["track_id"] for row in tracks} == {"1"}
        assert all(row["class_id"] == "5" for row in tracks)  # .15 car cannot initiate
        assert points[0]["timestamp_s"] == "0.0"
        assert len({p["timestamp_s"] for p in points}) == len(points)
        assert {row["run_id"] for row in points} == {manifest.run_id}
        assert summary["tracker"]["total_confirmed_tracks"] == 1
        assert json.loads((output / "summary.json").read_text())["tracker"]["tracking_ms"] > 0
        assert not list(output.glob("*.partial"))


def test_tracks_render_ids_without_mutating_pixels_or_bridging_missing_frame():
    from vision.rendering.tracks import render_tracks

    f = frame(0)
    t = Track(track_id=1, class_id=2, confidence=0.9, bbox_xyxy=(10.0, 10.0, 50.0, 50.0))
    h = TrackHistoryManager("r", "v", 3, csv.writer(io.StringIO()), csv.writer(io.StringIO()))
    h.update(f, (t,))
    moved = t.model_copy(update={"bbox_xyxy": (110.0, 10.0, 150.0, 50.0)})
    h.update(replace(f, frame_index=2, timestamp_s=0.1), (moved,))
    rendered, count = render_tracks(f.pixels, (moved,), h.histories, {2: "car"}, 0.25)
    assert count == 1 and rendered.any() and not f.pixels.any()
    assert not rendered[50, 80].any()  # no invented line across the missing frame
    continuous = TrackHistoryManager(
        "r", "v", 3, csv.writer(io.StringIO()), csv.writer(io.StringIO())
    )
    continuous.update(f, (t,))
    continuous.update(replace(f, frame_index=1, timestamp_s=0.04), (moved,))
    drawn, _ = render_tracks(f.pixels, (moved,), continuous.histories, {2: "car"}, 0.25)
    assert drawn[50, 80].any()
    lost = t.model_copy(update={"state": "lost", "confidence": None})
    rendered, count = render_tracks(f.pixels, (lost,), h.histories, {2: "car"}, 0.25)
    assert count == 0 and not rendered.any()


def test_missing_tracker_dependencies_produce_actionable_error(monkeypatch):
    from importlib.metadata import PackageNotFoundError

    from vision.trackers import bytetrack

    def missing(name):
        raise PackageNotFoundError(name)

    monkeypatch.setattr(bytetrack, "version", missing)
    with pytest.raises(VisionError) as error:
        bytetrack.ByteTrackAdapter(TrackerConfig())
    assert error.value.code == "missing_detector_extra"


@pytest.mark.tracker
def test_tracker_failure_retains_partial_evidence_without_completion(tmp_path):
    class CrowdedDetector(FixtureDetector):
        def detect(self, pixels):
            batch = super().detect(pixels)
            return replace(
                batch,
                detections=tuple(
                    d.model_copy(update={"confidence": 0.9}) for d in batch.detections
                ),
            )

    source = tmp_path / "source.mp4"
    generate_sample(source, frames=2)
    output = tmp_path / "failed"
    config = ProcessingConfig(
        video_id="test",
        detector_model_id="yolo11n-coco",
        tracker_config_id="bytetrack-default",
        tracker=TrackerConfig(max_live_tracks=1),
    )
    with pytest.raises(VisionError, match="limit"):
        process_video(source, output, config=config, detector=CrowdedDetector())
    assert json.loads((output / "failure.json").read_text())["error_code"] == "tracking_limit"
    assert not (output / "summary.json").exists()
    assert not (output / "trajectories.csv").exists()
    assert (output / "trajectories.csv.partial").exists()
