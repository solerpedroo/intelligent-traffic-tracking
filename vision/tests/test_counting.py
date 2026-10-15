"""Exact synthetic crossing oracles; real ByteTrack integration is separately marked."""

import csv
import io
import json
from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.generate_sample import generate_sample
from vision.contracts import CountingConfig, FramePacket, LineConfig, ProcessingConfig, Track
from vision.contracts.errors import VisionError
from vision.counting.export import CrossingSink
from vision.counting.lines import LineCounter
from vision.geometry import PixelLine
from vision.pipeline.cli import main
from vision.pipeline.video import process_video
from vision.tests.test_detection import FixtureDetector

LINE = LineConfig(line_id="gate", start=(0.25, 0.5), end=(0.75, 0.5))


def config(**changes):
    return CountingConfig(lines=(LINE,), **changes)


def counter(**changes):
    return LineCounter(config(**changes), 100, 100, "run", "video")


def frame(index, timestamp=None):
    return FramePacket(
        index,
        float(index / 25 if timestamp is None else timestamp),
        np.zeros((100, 100, 3), dtype=np.uint8),
    )


def track(point, track_id=1, class_id=2, state="observed"):
    x, y = point
    return Track(
        track_id=track_id,
        class_id=class_id,
        state=state,
        confidence=0.15 if state == "observed" else None,
        bbox_xyxy=(float(x - 5), float(y - 10), float(x + 5), float(y)),
    )


def run(points, subject=None):
    subject = subject or counter()
    events = []
    for i, point in enumerate(points):
        items = (track(point),) if point is not None else (track((50, 50), state="lost"),)
        events.extend(subject.update(frame(i), items))
    return subject, events


@pytest.mark.parametrize(
    "line,points",
    [
        (LINE, [(50, 20), (50, 25), (50, 60), (50, 65)]),
        (
            LineConfig(line_id="v", start=(0.5, 0.25), end=(0.5, 0.75)),
            [(80, 50), (75, 50), (40, 50), (35, 50)],
        ),
        (
            LineConfig(line_id="d", start=(0.2, 0.2), end=(0.8, 0.8)),
            [(70, 30), (65, 35), (35, 65), (30, 70)],
        ),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_orientation_and_reversed_endpoints(line, points, reverse):
    if reverse:
        line = LineConfig(line_id=line.line_id, start=line.end, end=line.start)
    subject = LineCounter(CountingConfig(lines=(line,)), 100, 100, "r", "v")
    _, events = run(points, subject)
    assert len(events) == 1
    event = events[0]
    assert event.direction == ("B_TO_A" if reverse else "A_TO_B")
    assert event.frame_index == 3 and event.timestamp_s == 0.12
    assert event.evidence_start_frame == 1 and event.evidence_start_s == 0.04
    assert event.observed_count == 4 and event.intersection_xy is not None
    assert subject.summary()["total_events"] == 1


@pytest.mark.parametrize(
    "points",
    [
        [(50, 20), (50, 25), (50, 50), (50, 25), (50, 20)],  # touch only
        [(50, 20), (50, 25), (50, 49), (50, 51), (50, 48), (50, 52), (50, 25)],  # jitter
        [(90, 20), (90, 25), (90, 60), (90, 65)],  # extension
        [(50, 20), (50, 25), (90, 48), (90, 52), (50, 60), (50, 65)],  # detour through band
        [
            (50, 20),
            (50, 25),
            (50, 50),
            (90, 50),
            (90, 60),
            (90, 65),
        ],  # along line then outside endpoint
        [(50, 50), (50, 50), (50, 60), (50, 65)],  # starts in band
        [(50, 20), (50, 25), (50, 50), (50, 50)],  # ends in band
        [(50, 20), (50, 25), None, (50, 60), (50, 65)],  # default forbids missing frame
        [(50, 20), (50, 25), (101, 60), (50, 60), (50, 65)],  # out-of-image breaks evidence
    ],
)
def test_no_crossing_without_valid_path_evidence(points):
    subject, events = run(points)
    assert events == [] and subject.summary()["total_events"] == 0


def test_band_preserves_origin_and_counts_only_after_opposite_side_is_stable():
    subject, events = run([(50, y) for y in (20, 25, 48, 49, 50, 51, 52, 60, 65)])
    assert len(events) == 1 and events[0].frame_index == 8
    assert events[0].evidence_start_frame == 1
    assert events[0].intersection_xy == (50, 50)
    assert subject.summary()["by_line_direction"][0]["count"] == 1


def test_finite_endpoint_is_inclusive_but_collinear_motion_is_not_a_crossing():
    _, events = run([(25, y) for y in (20, 25, 60, 65)])
    assert len(events) == 1
    line = PixelLine.from_config(LINE, 100, 100)
    assert line.intersection((25, 50), (75, 50)) is None
    assert line.intersection((90, 20), (90, 60)) is None


def test_short_track_is_not_counted_later_without_another_crossing():
    _, events = run([(50, y) for y in (20, 25, 60, 65, 70, 75)], counter(min_observations=5))
    assert events == []


def test_gap_is_limited_in_both_frames_and_media_seconds():
    _, allowed = run([(50, 20), (50, 25), None, (50, 60), (50, 65)], counter(max_gap_frames=2))
    assert len(allowed) == 1
    subject = counter(max_gap_frames=2, max_gap_s=0.1)
    events = []
    for i, (y, time) in enumerate(((20, 0.0), (25, 0.04), (60, 1.0), (65, 1.04))):
        events.extend(subject.update(frame(i, time), (track((50, y)),)))
    assert events == []


def test_return_deduplicates_each_direction_independently_and_reset_changes_run():
    points = [(50, y) for y in (20, 25, 60, 65, 25, 20, 60, 65, 25, 20)]
    subject, events = run(points)
    assert [e.direction for e in events] == ["A_TO_B", "B_TO_A"]
    subject.reset("new-run", "new-video")
    _, again = run(points, subject)
    assert len(again) == 2 and {e.run_id for e in again} == {"new-run"}


def test_two_lines_classes_and_lost_states():
    lines = (LINE, LineConfig(line_id="lower", start=(0.25, 0.7), end=(0.75, 0.7)))
    subject = LineCounter(CountingConfig(lines=lines), 100, 100, "r", "v")
    events = []
    for i, y in enumerate((20, 25, 60, 65, 80, 85)):
        events.extend(subject.update(frame(i), (track((45, y)), track((55, y), 2, 5))))
    assert len(events) == 4
    assert {(e.line_id, e.class_id) for e in events} == {
        ("gate", 2),
        ("gate", 5),
        ("lower", 2),
        ("lower", 5),
    }
    assert len(subject.summary()["by_line_class_direction"]) == 4


def test_disappearance_prunes_state_and_new_id_does_not_inherit_anchor():
    subject = counter()
    subject.update(frame(0), (track((50, 20)),))
    subject.update(frame(1), (track((50, 25)),))
    subject.update(frame(2), ())
    assert subject.states == {}
    assert subject.update(frame(3), (track((50, 60), 2),)) == ()
    assert subject.update(frame(4), (track((50, 65), 2),)) == ()


def test_dedup_flags_survive_a_gap_but_geometry_does_not():
    subject, events = run([(50, y) for y in (20, 25, 60, 65)])
    subject.update(frame(4), (track((50, 65), state="lost"),))
    for i, y in enumerate((20, 25, 60, 65), start=5):
        events.extend(subject.update(frame(i), (track((50, y)),)))
    assert len(events) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"lines": (LINE, LINE)},
        {"hysteresis_px": -1.0},
        {"max_gap_s": 0.0},
        {"window_s": float("nan")},
        {"min_observations": 1},
        {"stable_observations": 0},
    ],
)
def test_invalid_config(changes):
    with pytest.raises(ValidationError):
        CountingConfig(**changes)


@pytest.mark.parametrize(
    "start,end",
    [((0.5, 0.5), (0.5, 0.5)), ((-0.1, 0.5), (0.5, 0.5)), ((0.0, 0.0), (1.0, float("inf")))],
)
def test_invalid_line(start, end):
    with pytest.raises(ValidationError):
        LineConfig(line_id="x", start=start, end=end)


def test_lines_require_tracker():
    with pytest.raises(ValidationError, match="require tracker"):
        ProcessingConfig(video_id="v", counting=config())


def test_order_class_and_limit_contracts():
    subject = counter()
    subject.update(frame(0), (track((50, 20)),))
    with pytest.raises(VisionError, match="consecutive"):
        subject.update(frame(2), ())
    with pytest.raises(VisionError, match="class"):
        subject.update(frame(1), (track((50, 20), class_id=5),))
    with pytest.raises(VisionError, match="Duplicate"):
        counter().update(frame(0), (track((50, 20)), track((50, 25))))


def test_counter_memory_depends_on_live_tracks_and_lines_not_video_length():
    subject = counter()
    for i in range(1000):
        subject.update(frame(i), (track((50, 20 if i % 2 == 0 else 80), i + 1),))
        assert len(subject.states) == 1
    subject.update(frame(1000), ())
    assert subject.states == {}


def test_sparse_window_streaming_and_event_reconciliation():
    subject, events = run([(50, y) for y in (20, 25, 60, 65, 25, 20)])
    csv_events, csv_windows = io.StringIO(), io.StringIO()
    sink = CrossingSink(csv.writer(csv_events), csv.writer(csv_windows), 0.1, "run", "video")
    for event in events:
        sink.write(event.timestamp_s, (event,))
    sink.flush()
    rows = list(csv.reader(io.StringIO(csv_events.getvalue())))
    windows = list(csv.reader(io.StringIO(csv_windows.getvalue())))
    assert len(rows) == subject.summary()["total_events"] == 2
    assert sum(int(w[-1]) for w in windows) == 2
    assert len(windows) == 2 and sink.counts == {}
    assert rows[0][CrossingSink.event_fields.index("intersection_xy")] == "50.0,50.0"


def test_cli_rejects_counting_without_tracking_before_processing(tmp_path, capsys):
    path = tmp_path / "lines.json"
    path.write_text(config().model_dump_json())
    assert (
        main(
            [
                "process",
                str(tmp_path / "missing.mp4"),
                "--output-dir",
                str(tmp_path / "out"),
                "--counting-config",
                str(path),
            ]
        )
        == 2
    )
    assert "require tracker" in json.loads(capsys.readouterr().err)["error"]


@pytest.mark.tracker
def test_pipeline_real_bytetrack_counts_weak_detections_independent_of_overlay(
    tmp_path, monkeypatch
):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Counter integration must not connect to the network")

    monkeypatch.setattr(socket.socket, "connect", denied)

    class MovingDetector(FixtureDetector):
        def detect(self, pixels):
            batch = super().detect(pixels)
            y = 20 + self.calls * 3
            detection = batch.detections[1].model_copy(
                update={
                    "bbox_xyxy": (60.0, float(y - 20), 100.0, float(y)),
                    "confidence": 0.9 if self.calls <= 3 else 0.15,
                }
            )
            return replace(batch, detections=(detection,))

    source = tmp_path / "source.mp4"
    generate_sample(source, frames=20)
    output = tmp_path / "out"
    cfg = ProcessingConfig(
        video_id="v",
        detector_model_id="yolo11n-coco",
        tracker_config_id="bytetrack-default",
        counting=CountingConfig(
            lines=(LineConfig(line_id="gate", start=(0.25, 0.5), end=(0.75, 0.5)),)
        ),
    )
    result = process_video(source, output, config=cfg, detector=MovingDetector())
    events = list(csv.DictReader(io.StringIO((output / "crossing_events.csv").read_text())))
    windows = list(csv.DictReader(io.StringIO((output / "crossing_windows.csv").read_text())))
    assert result["counting"]["total_events"] == len(events) == 1
    assert events[0]["direction"] == "A_TO_B" and events[0]["class_id"] == "5"
    assert sum(int(w["count"]) for w in windows) == 1
    assert result["detector"]["boxes_rendered"] == 3
    assert not list(output.glob("*.partial"))


def test_decimal_window_boundary_does_not_fall_into_previous_bucket():
    from vision.contracts import CrossingEvent

    windows = io.StringIO()
    sink = CrossingSink(csv.writer(io.StringIO()), csv.writer(windows), 0.1, "r", "v")
    event = CrossingEvent(
        run_id="r",
        video_id="v",
        frame_index=3,
        timestamp_s=0.3,
        track_id=1,
        class_id=2,
        line_id="gate",
        direction="A_TO_B",
    )
    sink.write(0.3, (event,))
    sink.flush()
    row = next(csv.reader(io.StringIO(windows.getvalue())))
    assert row[2:4] == ["0.3", "0.4"]


def test_partial_or_future_crossing_evidence_is_rejected():
    from vision.contracts import CrossingEvent

    event = dict(
        run_id="r",
        video_id="v",
        frame_index=3,
        timestamp_s=0.3,
        track_id=1,
        class_id=2,
        line_id="gate",
        direction="A_TO_B",
    )
    with pytest.raises(ValidationError, match="complete"):
        CrossingEvent(**event, evidence_start_frame=1)
    with pytest.raises(ValidationError, match="precede"):
        CrossingEvent(
            **event,
            evidence_start_frame=4,
            evidence_start_s=0.2,
            intersection_xy=(50.0, 50.0),
            observed_count=4,
        )


def test_empty_crossing_exports_have_headers_and_zero_summary(tmp_path):
    # No fake tracker: the real state machine exports valid empty data independently.
    subject = counter()
    output = io.StringIO()
    rows = csv.writer(output)
    rows.writerow(CrossingSink.event_fields)
    sink = CrossingSink(rows, csv.writer(io.StringIO()), 60.0, "r", "v")
    sink.write(0.0, subject.update(frame(0), ()))
    sink.flush()
    assert len(list(csv.reader(io.StringIO(output.getvalue())))) == 1
    assert subject.summary()["total_events"] == 0
    assert [x["count"] for x in subject.summary()["by_line_direction"]] == [0, 0]


def test_gap_seconds_boundary_is_inclusive_despite_float_rounding():
    subject = counter(max_gap_s=0.1)
    events = []
    for i, y in enumerate((20, 25, 60, 65)):
        events.extend(subject.update(frame(i, (0.1, 0.2, 0.3, 0.4)[i]), (track((50, y)),)))
    assert len(events) == 1


def test_render_lines_clamps_display_and_keeps_input_unchanged():
    from vision.rendering.lines import render_lines

    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    subject = LineCounter(
        CountingConfig(lines=(LineConfig(line_id="edge", start=(0.0, 1.0), end=(1.0, 1.0)),)),
        100,
        100,
        "r",
        "v",
    )
    output = render_lines(pixels, subject.lines, subject.summary())
    assert not pixels.any() and output[99, 50].any()


def test_manual_smoke_comparison_is_one_to_one_and_reports_disagreements():
    from scripts.smoke_counting import compare_annotations

    annotation = {
        "purpose": "development_sanity_check_not_benchmark_ground_truth",
        "confirmation_tolerance_frames": 3,
        "events": [
            {
                "object_note": "car",
                "line_id": "gate",
                "class_id": 2,
                "direction": "A_TO_B",
                "crossing_frame_interval": [10, 12],
            }
        ],
    }
    detected = {"line_id": "gate", "class_id": "2", "direction": "A_TO_B", "frame_index": "14"}
    matched = compare_annotations([detected], annotation)
    assert len(matched["matched"]) == 1 and not matched["missing"] and not matched["unexpected"]
    mismatch = compare_annotations([detected, detected.copy()], annotation)
    assert len(mismatch["unexpected"]) == 1
    assert len(compare_annotations([], annotation)["missing"]) == 1


def test_zero_hysteresis_and_single_observation_sides_are_explicitly_supported():
    _, events = run(
        [(50, 20), (50, 60)], counter(hysteresis_px=0.0, min_observations=2, stable_observations=1)
    )
    assert len(events) == 1 and events[0].frame_index == 1
