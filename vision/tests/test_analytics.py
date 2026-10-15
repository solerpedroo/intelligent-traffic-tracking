"""ROI/dwell and heatmap oracles use original media time and exact synthetic paths."""

import csv
import io
import json
from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.generate_sample import generate_sample
from vision.analytics.heatmaps import HeatmapAccumulator
from vision.analytics.zones import ZoneAnalytics
from vision.contracts import (
    AnalyticsConfig,
    CountingConfig,
    FramePacket,
    HeatmapConfig,
    LineConfig,
    ProcessingConfig,
    Track,
    ZoneConfig,
)
from vision.contracts.errors import VisionError
from vision.geometry.polygons import contains
from vision.pipeline.cli import main
from vision.pipeline.video import process_video
from vision.rendering.heatmaps import HeatmapWriter, heatmap_preview, smooth_counts
from vision.rendering.zones import render_zones
from vision.tests.test_detection import FixtureDetector

SQUARE = ZoneConfig(zone_id="roi", vertices=((0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)))


def frame(index, time=None):
    return FramePacket(
        index, float(index / 25 if time is None else time), np.zeros((100, 100, 3), dtype=np.uint8)
    )


def track(x=50.0, y=50.0, track_id=1, class_id=2, state="observed"):
    return Track(
        track_id=track_id,
        class_id=class_id,
        state=state,
        confidence=0.15 if state == "observed" else None,
        bbox_xyxy=(float(x - 5), float(y - 10), float(x + 5), float(y)),
    )


def analytics(**changes):
    visits = []
    subject = ZoneAnalytics(
        AnalyticsConfig(zones=(SQUARE,), **changes), 100, 100, (2, 5), "run", "video", visits.append
    )
    return subject, visits


@pytest.mark.parametrize(
    "point,expected",
    [
        ((0.2, 0.2), True),
        ((0.2, 0.5), True),
        ((0.8, 0.8), True),
        ((0.5, 0.8), True),
        ((0.5, 0.5), True),
        ((0.1, 0.5), False),
        ((0.9, 0.9), False),
    ],
)
def test_polygon_includes_edges_and_vertices_in_either_winding(point, expected):
    assert contains(SQUARE.vertices, point) == expected
    assert contains(tuple(reversed(SQUARE.vertices)), point) == expected


def test_concave_polygon_does_not_fill_its_bounding_box():
    vertices = ((0.1, 0.1), (0.9, 0.1), (0.9, 0.4), (0.4, 0.4), (0.4, 0.9), (0.1, 0.9))
    zone = ZoneConfig(zone_id="concave", vertices=vertices)
    assert contains(zone.vertices, (0.2, 0.8))
    assert not contains(zone.vertices, (0.7, 0.7))


@pytest.mark.parametrize(
    "vertices",
    [
        ((0.1, 0.1), (0.2, 0.2)),
        ((0.1, 0.1), (0.2, 0.2), (0.3, 0.3)),
        ((0.1, 0.1), (0.8, 0.8), (0.1, 0.8), (0.8, 0.1)),
        ((0.1, 0.1), (0.8, 0.1), (0.8, 0.8), (0.1, 0.1)),
        ((0.1, 0.1), (0.8, 0.1), (0.4, 0.1), (0.8, 0.8), (0.1, 0.8)),
        ((0.1, 0.1), (0.8, 0.1), (0.8, 0.8), (0.5, 0.1), (0.1, 0.8)),
        ((-0.1, 0.1), (0.8, 0.1), (0.8, 0.8)),
        ((0.1, 0.1), (float("nan"), 0.1), (0.8, 0.8)),
    ],
)
def test_invalid_polygons_rejected(vertices):
    with pytest.raises(ValidationError):
        ZoneConfig(zone_id="invalid", vertices=vertices)


def test_entry_exit_and_irregular_timestamps_use_only_inside_inside_intervals():
    subject, visits = analytics()
    events = []
    for i, (x, time) in enumerate(((10, 0.0), (30, 0.1), (50, 0.35), (90, 0.4))):
        batch = subject.update(frame(i, time), (track(x),))
        events.extend(batch.events)
        assert batch.occupancy[0][-1] == (1 if 20 <= x <= 80 else 0)
    assert [e.event_type for e in events] == ["zone_enter", "zone_exit"]
    assert len(visits) == 1
    visit = visits[0]
    assert visit.observed_dwell_s == pytest.approx(0.25)
    assert visit.first_inside_s == 0.1 and visit.last_inside_s == 0.35 and visit.closed_s == 0.4
    assert not visit.left_censored and not visit.right_censored
    assert subject.summary()["by_zone_class"][0]["observed_dwell_s"] == pytest.approx(0.25)


def test_first_and_last_inside_are_censored_without_extrapolating_frame_duration():
    subject, visits = analytics()
    first = subject.update(replace(frame(10, 3.0), duration_s=1.0), (track(),))
    subject.update(replace(frame(11, 3.2), duration_s=1.0), (track(),))
    assert first.events[0].event_type == "boundary_censored"
    assert first.events[0].reason == "selection_start"
    end = subject.finish()
    assert end[0].reason == "selection_end" and end[0].frame_index == 11
    assert visits[0].left_censored and visits[0].right_censored
    assert visits[0].observed_dwell_s == pytest.approx(0.2)
    assert subject.states == {} and subject.finish() == ()
    with pytest.raises(VisionError):
        subject.update(frame(12, 3.3), ())


@pytest.mark.parametrize("absence", ["lost", "predicted", "removed", "out_of_image"])
def test_absence_closes_with_loss_not_exit_and_does_not_bridge_dwell(absence):
    subject, visits = analytics()
    subject.update(frame(0), (track(),))
    subject.update(frame(1), (track(),))
    items = (
        ()
        if absence == "removed"
        else (track(x=101.0) if absence == "out_of_image" else track(state=absence),)
    )
    lost = subject.update(frame(2), items)
    assert lost.events[0].event_type == "observation_lost"
    assert visits[0].right_censored and visits[0].observed_dwell_s == 0.04
    recovered = subject.update(frame(3), (track(),))
    assert recovered.events[0].event_type == "boundary_censored"
    subject.finish()
    assert len(visits) == 2 and visits[1].observed_dwell_s == 0
    assert subject.summary()["by_zone_class"][0]["zone_exit"] == 0


def test_timestamp_gap_censors_then_starts_a_new_visit_without_false_entry():
    subject, visits = analytics(max_gap_s=0.1)
    subject.update(frame(0, 0.0), (track(),))
    batch = subject.update(frame(1, 2.0), (track(),))
    assert [(e.event_type, e.reason) for e in batch.events] == [
        ("observation_lost", "timestamp_gap"),
        ("boundary_censored", "after_observation_loss"),
    ]
    subject.finish()
    assert len(visits) == 2 and sum(v.observed_dwell_s for v in visits) == 0


def test_roi_gap_seconds_is_inclusive_despite_float_rounding():
    subject, visits = analytics(max_gap_s=0.1)
    for i, time in enumerate((0.1, 0.2, 0.3, 0.4)):
        subject.update(frame(i, time), (track(),))
    subject.finish()
    assert len(visits) == 1 and visits[0].observed_dwell_s == pytest.approx(0.3)


def test_overlapping_zones_and_classes_count_independently_and_preserve_zero_rows():
    other = ZoneConfig(zone_id="overlap", vertices=SQUARE.vertices)
    visits = []
    subject = ZoneAnalytics(
        AnalyticsConfig(zones=(SQUARE, other)), 100, 100, (2, 5), "r", "v", visits.append
    )
    batch = subject.update(frame(0), (track(), track(track_id=2, class_id=5)))
    assert len(batch.events) == 4 and [row[-1] for row in batch.occupancy] == [1, 1, 1, 1]
    assert subject.max_occupancy == {"roi": 2, "overlap": 2}
    empty = subject.update(frame(1), ())
    assert [row[-1] for row in empty.occupancy] == [0, 0, 0, 0]
    assert len(visits) == 4


def test_reentry_creates_separate_visits_and_reset_clears_all_state():
    subject, visits = analytics()
    for i, x in enumerate((10, 30, 50, 90, 30, 50, 90)):
        subject.update(frame(i), (track(x),))
    assert len(visits) == 2 and [v.visit_id for v in visits] == [1, 2]
    assert all(not v.left_censored and not v.right_censored for v in visits)
    subject.reset("new-run", "new-video")
    batch = subject.update(frame(100, 4.0), (track(),))
    assert batch.events[0].visit_id == 1 and batch.events[0].run_id == "new-run"
    assert subject.summary()["total_visits"] == 1


def test_no_observations_produce_zero_occupancy_no_visits_or_events():
    subject, visits = analytics()
    for i in range(3):
        batch = subject.update(frame(i), ())
        assert batch.events == () and all(row[-1] == 0 for row in batch.occupancy)
    assert subject.finish() == () and visits == []
    assert subject.summary()["max_observed_occupancy"] == {"roi": 0}


def test_live_state_is_bounded_and_order_class_limits_are_enforced():
    subject, visits = analytics()
    for i in range(500):
        subject.update(frame(i), (track(track_id=i + 1),))
        assert len(subject.states) == 1
    subject.update(frame(500), ())
    assert subject.states == {} and len(visits) == 500
    with pytest.raises(VisionError, match="consecutive"):
        subject.update(frame(502), ())
    subject.reset("r", "v")
    subject.update(frame(0), (track(),))
    with pytest.raises(VisionError, match="stable"):
        subject.update(frame(1), (track(class_id=5),))
    with pytest.raises(VisionError, match="Duplicate"):
        analytics()[0].update(frame(0), (track(), track()))


@pytest.mark.parametrize(
    "settings",
    [
        {"zones": (SQUARE, SQUARE)},
        {"max_gap_s": 0.0},
        {"heatmap": HeatmapConfig(enabled=True, class_ids=(2,))},
    ],
)
def test_config_requires_tracker_and_rejects_duplicate_zones(settings):
    with pytest.raises(ValidationError):
        cfg = AnalyticsConfig(**settings)
        ProcessingConfig(video_id="v", analytics=cfg)


@pytest.mark.parametrize(
    "changes",
    [
        {"class_ids": (2, 2)},
        {"grid_width": 0},
        {"grid_height": 257},
        {"sigma_cells": -1.0},
        {"window_s": 0.0},
        {"weighting": "seconds"},
    ],
)
def test_invalid_heatmap_controls(changes):
    with pytest.raises(ValidationError):
        HeatmapConfig(**changes)


def test_heatmap_exact_class_cells_border_and_empty_windows_not_time_weighted():
    emitted = []
    cfg = HeatmapConfig(enabled=True, grid_width=10, grid_height=10, window_s=1.0, sigma_cells=0.0)
    accumulator = HeatmapAccumulator(
        cfg,
        100,
        100,
        (2, 5),
        lambda bucket, grids: emitted.append((bucket, {k: v.copy() for k, v in grids.items()})),
    )
    accumulator.update(
        frame(0, 0.0), (track(0.0, 0.0), track(100.0, 100.0, track_id=2, class_id=5))
    )
    accumulator.update(
        frame(1, 0.9),
        (track(0.0, 0.0), track(110.0, 50.0, track_id=3), track(state="lost", track_id=4)),
    )
    accumulator.update(frame(2, 1.0), ())
    accumulator.update(frame(3, 3.0), (track(50.0, 50.0),))
    accumulator.finish()
    assert [bucket for bucket, _ in emitted] == [0, 1, 3]
    assert emitted[0][1][2][0, 0] == 2 and emitted[0][1][5][9, 9] == 1
    assert emitted[1][1][2].sum() == 0 and emitted[2][1][2][5, 5] == 1
    assert accumulator.summary()["class_observations"] == {"2": 3, "5": 1}
    assert accumulator.windows == 3 and accumulator.grids == {}
    accumulator.reset()
    assert accumulator.summary()["class_observations"] == {"2": 0, "5": 0}
    accumulator.update(frame(0, 0.0), ())
    accumulator.finish()


def test_heatmap_decimal_boundary_subset_order_and_class_validation():
    emitted = []
    cfg = HeatmapConfig(enabled=True, window_s=1.0, class_ids=(5,))
    heatmap = HeatmapAccumulator(
        cfg, 100, 100, (2, 5), lambda bucket, grids: emitted.append(bucket)
    )
    heatmap.update(frame(0, 2.0), (track(), track(class_id=5, track_id=2)))
    with pytest.raises(VisionError):
        heatmap.update(frame(2, 2.1), ())
    heatmap.finish()
    assert emitted == [2] and heatmap.total_observations == {5: 1}
    with pytest.raises(VisionError, match="class IDs"):
        HeatmapAccumulator(cfg, 100, 100, (2,), lambda *a: None)
    with pytest.raises(VisionError):
        HeatmapAccumulator(HeatmapConfig(), 100, 100, tuple(range(17)), lambda *a: None)


@pytest.mark.parametrize("sigma", [0.0, 0.5, 1.0, 4.0])
def test_gaussian_smoothing_preserves_raw_mass_even_at_corner(sigma):
    raw = np.zeros((10, 10), dtype=np.uint64)
    raw[0, 0] = 7
    original = raw.copy()
    smoothed = smooth_counts(raw, sigma)
    np.testing.assert_array_equal(raw, original)
    assert smoothed.sum() == pytest.approx(7.0) and (smoothed >= 0).all()
    if sigma:
        assert smoothed[1, 1] > 0
    preview = heatmap_preview(smoothed)
    assert preview.shape == (10, 10, 3) and preview.dtype == np.uint8
    assert not heatmap_preview(np.zeros((10, 10))).any()


def test_heatmap_export_arrays_index_and_preview_reconcile(tmp_path):
    cfg = HeatmapConfig(enabled=True, grid_width=10, grid_height=10, window_s=1.0)
    output = io.StringIO()
    writer = HeatmapWriter(tmp_path / "maps", csv.writer(output), cfg, "r", "v")
    raw = np.zeros((10, 10), dtype=np.uint64)
    raw[9, 9] = 5
    writer(3, {2: raw})
    row = next(csv.reader(io.StringIO(output.getvalue())))
    assert row[2:5] == ["3.0", "4.0", "2"] and row[7] == "5"
    with np.load(tmp_path / "maps/window-00000003-class-2.npz", allow_pickle=False) as data:
        assert data["raw"].sum() == 5 and data["smoothed"].sum() == pytest.approx(5.0)
    assert (tmp_path / "maps/window-00000003-class-2.png").is_file()


def test_heatmap_memory_contains_only_current_window():
    count = 0

    def sink(bucket, grids):
        nonlocal count
        count += 1

    heatmap = HeatmapAccumulator(
        HeatmapConfig(enabled=True, grid_width=8, grid_height=8, window_s=1.0), 100, 100, (2,), sink
    )
    for i in range(200):
        heatmap.update(frame(i, float(i)), (track(),))
        assert sum(a.nbytes for a in heatmap.grids.values()) == 8 * 8 * 8
    heatmap.finish()
    assert count == 200


def test_zone_overlay_preserves_source_pixels_and_marks_boundaries():
    pixels = np.zeros((100, 100, 3), dtype=np.uint8)
    output = render_zones(pixels, (SQUARE,), {("roi", 2): 3})
    assert not pixels.any() and output[20, 50].any()


def test_cli_rejects_analytics_without_tracker(tmp_path, capsys):
    path = tmp_path / "zones.json"
    path.write_text(AnalyticsConfig(zones=(SQUARE,)).model_dump_json())
    assert (
        main(
            [
                "process",
                str(tmp_path / "missing.mp4"),
                "--output-dir",
                str(tmp_path / "out"),
                "--analytics-config",
                str(path),
            ]
        )
        == 2
    )
    assert "require tracker" in json.loads(capsys.readouterr().err)["error"]


@pytest.mark.tracker
def test_full_pipeline_zones_heatmaps_real_bytetrack_and_reset(tmp_path, monkeypatch):
    import socket

    def denied(*args, **kwargs):
        raise AssertionError("Analytics must never connect to network")

    monkeypatch.setattr(socket.socket, "connect", denied)
    source = tmp_path / "source.mp4"
    times = generate_sample(source, profile="vfr", frames=5)
    cfg = ProcessingConfig(
        video_id="v",
        detector_model_id="yolo11n-coco",
        tracker_config_id="bytetrack-default",
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
    for run in ("one", "two"):
        output = tmp_path / run
        result = process_video(source, output, config=cfg, detector=FixtureDetector())

        def rows(name, directory=output):
            return list(csv.DictReader(io.StringIO((directory / name).read_text())))

        visits = rows("zone_visits.csv")
        assert len(visits) == 1 and visits[0]["visit_id"] == "1"
        assert visits[0]["left_censored"] == visits[0]["right_censored"] == "True"
        assert float(visits[0]["observed_dwell_s"]) == pytest.approx(times[-1] - times[0])
        assert len(rows("zone_events.csv")) == 2
        occupancy = rows("zone_occupancy.csv")
        assert len(occupancy) == 5 * 6 and sum(int(r["observed_count"]) for r in occupancy) == 5
        index = rows("heatmap_index.csv")
        assert len(index) == 1 and index[0]["observations"] == "5"
        with np.load(output / index[0]["array_file"], allow_pickle=False) as data:
            assert data["raw"].sum() == 5 and data["smoothed"].sum() == pytest.approx(5.0)
        assert result["heatmap"]["class_observations"] == {"5": 5}
        assert result["zones"]["total_visits"] == 1 and not list(output.glob("*.partial"))
        assert result["counting"]["total_events"] == 0 and rows("crossing_events.csv") == []
        manifest = json.loads((output / "manifest.json").read_text())
        assert manifest["config"]["analytics"]["heatmap"]["weighting"] == "observations"
        assert {v["run_id"] for v in visits} == {manifest["run_id"]}


def test_heatmap_limits_and_finish_are_explicit_and_idempotent():
    emitted = []
    subject = HeatmapAccumulator(
        HeatmapConfig(enabled=True),
        100,
        100,
        (2,),
        lambda *args: emitted.append(args[0]),
        max_live_tracks=1,
    )
    with pytest.raises(VisionError, match="Duplicate"):
        subject.update(frame(0), (track(), track(track_id=2)))
    subject.update(frame(0), ())
    subject.finish()
    subject.finish()
    assert emitted == [0]
    with pytest.raises(VisionError):
        subject.update(frame(1), ())


def test_invalid_heatmap_class_fails_before_loading_model_or_creating_output(tmp_path):
    cfg = ProcessingConfig(
        video_id="v",
        detector_model_id="yolo11n-coco",
        tracker_config_id="bytetrack-default",
        analytics=AnalyticsConfig(heatmap=HeatmapConfig(enabled=True, class_ids=(99,))),
    )
    with pytest.raises(VisionError, match="class IDs"):
        process_video(
            tmp_path / "missing.mp4",
            tmp_path / "out",
            config=cfg,
            checkpoint=tmp_path / "missing.pt",
        )
    assert not (tmp_path / "out").exists()


def test_zone_visit_contract_rejects_impossible_dwell():
    from vision.contracts import ZoneVisit

    subject, visits = analytics()
    subject.update(frame(0), (track(),))
    subject.finish()
    values = visits[0].model_dump()
    values["observed_dwell_s"] = 1.0
    with pytest.raises(ValidationError, match="cannot exceed"):
        ZoneVisit(**values)


def test_collinear_forward_vertices_are_valid_without_self_touching():
    zone = ZoneConfig(
        zone_id="straight", vertices=((0.0, 0.0), (0.5, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    )
    assert contains(zone.vertices, (0.5, 0.5))


def test_failed_heatmap_preview_preserves_raw_numeric_evidence(tmp_path, monkeypatch):
    import cv2

    captured = io.StringIO()
    monkeypatch.setattr(cv2, "imencode", lambda *args: (False, None))
    writer = HeatmapWriter(
        tmp_path / "maps.partial", csv.writer(captured), HeatmapConfig(), "r", "v"
    )
    writer(0, {2: np.ones((8, 8), dtype=np.uint64)})
    assert writer.warnings[0]["code"] == "heatmap_preview_failed"
    assert not list((tmp_path / "maps.partial").glob("*.png"))
    row = next(csv.reader(io.StringIO(captured.getvalue())))
    assert row[-2].endswith(".npz") and row[-1] == ""
    with np.load(tmp_path / "maps.partial/window-00000000-class-2.npz", allow_pickle=False) as data:
        assert data["raw"].sum() == 64
