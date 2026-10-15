"""Oracle checks for scoring rules. They do not stand in for a frozen external benchmark."""

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vision.contracts.errors import VisionError
from vision.datasets.ground_truth import (
    GroundTruthBox,
    GroundTruthEvent,
    GroundTruthSequence,
    SplitRegistry,
    events_from_frame_intervals,
)
from vision.datasets.trackeval_export import mot_frame, write_sequence
from vision.evaluation.cli import main
from vision.evaluation.counting import evaluate_counting
from vision.evaluation.detection import average_precision, box_iou, evaluate_detection
from vision.evaluation.performance import evaluate_performance
from vision.evaluation.protocol import EvaluationProtocol
from vision.evaluation.report import aggregate_reports, block_reason, build_report

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = EvaluationProtocol.model_validate_json(
    (ROOT / "experiments/configs/evaluation-protocol.json").read_text()
)
SPLITS = SplitRegistry.model_validate_json((ROOT / "experiments/configs/splits.json").read_text())


def box(frame=0, class_id=2, track_id=1, bbox=(0.0, 0.0, 10.0, 10.0), ignore=False):
    return GroundTruthBox(
        frame_index=frame, class_id=class_id, track_id=track_id, bbox_xyxy=bbox, ignore=ignore
    )


def det(frame=0, class_id=2, confidence=0.9, bbox=(0.0, 0.0, 10.0, 10.0)):
    return {
        "frame_index": frame,
        "class_id": class_id,
        "confidence": confidence,
        "bbox_xyxy": bbox,
    }


def event(start, end=None, class_id=2, line_id="gate", direction="A_TO_B"):
    return GroundTruthEvent(
        line_id=line_id,
        class_id=class_id,
        direction=direction,
        start_s=start,
        end_s=start if end is None else end,
    )


def pred_event(timestamp, class_id=2, line_id="gate", direction="A_TO_B"):
    return {
        "line_id": line_id,
        "class_id": class_id,
        "direction": direction,
        "timestamp_s": timestamp,
    }


def test_committed_protocol_and_splits_are_not_a_frozen_benchmark():
    assert PROTOCOL.detection_iou_thresholds[0] == 0.5
    assert PROTOCOL.detection_iou_thresholds[-1] == 0.95
    assert len(PROTOCOL.detection_iou_thresholds) == 10
    assert PROTOCOL.counting_tolerance_s == 0.5
    assert SPLITS.test_split_frozen is False
    assert all(item.sha256 is None for item in SPLITS.sequences)
    assert block_reason(SPLITS, "SDD-GATES-0") == "test_split_not_frozen"


def test_trackeval_frames_are_one_based_and_keep_gaps(tmp_path):
    assert mot_frame(0) == 1
    exported = write_sequence(
        tmp_path,
        "seq",
        [
            {"frame_index": 0, "track_id": 1, "bbox_xyxy": (1.0, 2.0, 11.0, 22.0)},
            {"frame_index": 2, "track_id": 1, "bbox_xyxy": (1.0, 2.0, 11.0, 22.0)},
        ],
        [{"frame_index": 2, "track_id": 1, "bbox_xyxy": (1.0, 2.0, 11.0, 22.0), "confidence": 0.5}],
        frame_rate=10,
        width=100,
        height=80,
    )
    gt_rows = list(csv.reader(exported["gt"].read_text().splitlines()))
    assert [row[0] for row in gt_rows] == ["1", "3"]
    assert gt_rows[0][2:6] == ["1.0", "2.0", "10.0", "20.0"]
    assert "\n2," not in exported["gt"].read_text()
    assert exported["seq_length"] == 3
    with pytest.raises(VisionError, match="positive"):
        write_sequence(
            tmp_path / "zero",
            "seq",
            [{"frame_index": 0, "track_id": 0, "bbox_xyxy": (0.0, 0.0, 2.0, 2.0)}],
            [],
            frame_rate=10,
            width=10,
            height=10,
        )


def test_detection_perfect_partial_and_known_iou():
    perfect = evaluate_detection([det()], [box()], PROTOCOL)
    assert perfect["mean_average_precision_50_95"] == 1
    assert perfect["operating_point_iou_0_5"]["2"]["precision"] == 1
    assert perfect["operating_point_iou_0_5"]["2"]["recall"] == 1
    shifted = evaluate_detection([det(bbox=(0.0, 0.0, 10.0, 6.0))], [box()], PROTOCOL)
    assert box_iou((0.0, 0.0, 10.0, 10.0), (0.0, 0.0, 10.0, 6.0)) == pytest.approx(0.6)
    assert shifted["mean_average_precision_50_95"] == pytest.approx(0.3)
    missed = evaluate_detection([], [box(), box(frame=1)], PROTOCOL)
    assert missed["operating_point_iou_0_5"]["2"]["recall"] == 0
    assert missed["operating_point_iou_0_5"]["2"]["precision"] is None
    wrong_frame = evaluate_detection([det(frame=1)], [box(frame=0)], PROTOCOL)
    assert wrong_frame["operating_point_iou_0_5"]["2"]["true_positives"] == 0
    swapped = evaluate_detection([det(class_id=7)], [box(class_id=2), box(class_id=7)], PROTOCOL)
    assert swapped["average_precision_by_class"]["2"] == 0
    assert swapped["average_precision_by_class"]["7"] == 1
    ignored = evaluate_detection(
        [det(class_id=1), det()],
        [box(class_id=1), box()],
        PROTOCOL.model_copy(update={"ignored_class_ids": (1,)}),
    )
    assert list(ignored["average_precision_by_class"]) == ["2"]
    assert ignored["mean_average_precision_50_95"] == 1
    empty = evaluate_detection([det()], [], PROTOCOL)
    assert empty["status"] == "not_evaluated"
    assert empty["mean_average_precision_50_95"] is None
    assert average_precision([False, True], 1) == pytest.approx(0.5)


def test_ignore_boxes_and_scale_slices():
    result = evaluate_detection(
        [det(bbox=(0.0, 0.0, 10.0, 10.0))],
        [box(ignore=True), box(bbox=(20.0, 20.0, 28.0, 28.0))],
        PROTOCOL,
    )
    point = result["operating_point_iou_0_5"]["2"]
    assert point["false_positives"] == 0
    assert point["false_negatives"] == 1
    small = evaluate_detection([det()], [box()], PROTOCOL, scale="small")
    assert small["status"] == "evaluated"
    large = evaluate_detection([det()], [box()], PROTOCOL, scale="large")
    assert large["status"] == "not_evaluated"


def test_counting_tolerance_edges_zero_ground_truth_and_one_to_one():
    inside = evaluate_counting([pred_event(0.0)], [event(0.5)], PROTOCOL)
    outside = evaluate_counting([pred_event(-0.01)], [event(0.5)], PROTOCOL)
    assert inside["true_positives"] == 1
    assert outside["false_positives"] == 1 and outside["false_negatives"] == 1
    boundary = evaluate_counting([pred_event(0.0)], [event(0.5)], PROTOCOL)
    assert boundary["true_positives"] == 1
    exclusive = evaluate_counting([pred_event(1.01)], [event(0.0, 0.5)], PROTOCOL)
    assert exclusive["true_positives"] == 0
    double = evaluate_counting([pred_event(0.2), pred_event(0.2)], [event(0.2)], PROTOCOL)
    assert double["true_positives"] == 1 and double["false_positives"] == 1
    zeros = evaluate_counting([], [], PROTOCOL)
    assert zeros["absolute_error"] == 0
    assert zeros["relative_error"] is None
    assert zeros["precision"] is None and zeros["recall"] is None
    assert zeros["empty_agreement"] is True
    extra = evaluate_counting([pred_event(0.2), pred_event(0.2)], [], PROTOCOL)
    assert extra["absolute_error"] == 2 and extra["relative_error"] is None
    other_direction = evaluate_counting(
        [pred_event(0.2, direction="B_TO_A")], [event(0.2)], PROTOCOL
    )
    assert other_direction["true_positives"] == 0


def test_duplicate_identity_and_invalid_event_window_are_rejected():
    with pytest.raises(ValidationError, match="twice"):
        GroundTruthSequence(
            sequence_id="seq",
            split="development",
            boxes=(box(), box()),
        )
    with pytest.raises(ValidationError, match="precede"):
        event(0.4, 0.2)
    converted = events_from_frame_intervals(
        [
            {
                "line_id": "approach",
                "class_id": 2,
                "direction": "A_TO_B",
                "crossing_frame_interval": [7, 10],
            }
        ],
        25,
    )
    assert converted[0].start_s == pytest.approx(7 / 25)
    assert converted[0].end_s == pytest.approx(10 / 25)


def test_performance_does_not_turn_missing_samples_into_zero():
    missing = evaluate_performance(None, None)
    assert missing["status"] == "not_evaluated"
    assert missing["ram_bytes"] is None and missing["inference_fps"] is None
    measured = evaluate_performance(
        [
            {
                "decode_ms": "1",
                "preprocessing_ms": "0",
                "predict_ms": "0",
                "inference_ms": value,
                "postprocessing_ms": "0",
                "tracking_ms": "0",
                "counting_ms": "0",
                "analytics_ms": "0",
                "render_ms": "0",
                "encode_submit_ms": "0",
            }
            for value in ("1", "2", "3", "4")
        ],
        {"inference_fps": 10, "end_to_end_fps": 4, "elapsed_s": 1},
    )
    assert measured["stages"]["inference_ms"]["median_ms"] == 2.5
    assert measured["stages"]["inference_ms"]["p95_ms"] == 4
    assert measured["inference_fps"] == 10


def test_aggregate_skips_not_evaluated_instead_of_averaging_zero():
    sequence = GroundTruthSequence(sequence_id="seq", split="development", boxes=(box(),))
    scored = build_report(sequence, {"detections": [det()], "events": [], "tracks": None}, PROTOCOL)
    missing = build_report(sequence, {"detections": None, "events": None, "tracks": None}, PROTOCOL)
    summary = aggregate_reports([scored, missing])
    assert summary["mean_average_precision_50_95"] == 1
    assert summary["benchmark_sequences"] == 0


def test_cli_refuses_unfrozen_split_and_can_mark_development(tmp_path):
    truth = tmp_path / "gt.json"
    truth.write_text(
        GroundTruthSequence(
            sequence_id="SDD-GATES-0",
            split="test",
            events=(event(0.2),),
        ).model_dump_json()
    )
    predictions = tmp_path / "run"
    predictions.mkdir()
    (predictions / "detections.csv").write_text(
        "frame_index,class_id,confidence,x1,y1,x2,y2\n0,2,0.9,0,0,10,10\n",
        encoding="utf-8",
    )
    (predictions / "crossing_events.csv").write_text(
        "line_id,class_id,direction,timestamp_s\ngate,2,A_TO_B,0.2\n",
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    common = [
        "--ground-truth",
        str(truth),
        "--predictions",
        str(predictions),
        "--protocol",
        str(ROOT / "experiments/configs/evaluation-protocol.json"),
        "--splits",
        str(ROOT / "experiments/configs/splits.json"),
        "--output",
        str(output),
        "--frame-rate",
        "25",
        "--width",
        "100",
        "--height",
        "80",
    ]
    assert main(common) == 2
    assert not output.exists()
    assert main([*common, "--allow-development"]) == 0
    report = json.loads(output.read_text())
    assert report["claim"] == "development_not_benchmark"
    assert report["benchmark_eligible"] is False
    assert report["counting"]["true_positives"] == 1
    assert report["mot"]["reason"] == "missing_tracks"


@pytest.mark.evaluation
def test_trackeval_perfect_match_and_known_identity_switch(tmp_path):
    from vision.evaluation.mot import evaluate_mot

    truth = [box(frame=0), box(frame=1, bbox=(0.0, 0.0, 10.0, 10.0))]
    perfect = [
        {**det(frame=0), "track_id": 1},
        {**det(frame=1), "track_id": 1},
    ]
    switched = [
        {**det(frame=0), "track_id": 1},
        {**det(frame=1), "track_id": 2},
    ]
    kwargs = {
        "protocol": PROTOCOL,
        "class_id": 2,
        "sequence_id": "seq",
        "frame_rate": 10,
        "width": 100,
        "height": 100,
    }
    good = evaluate_mot(truth, perfect, work_dir=tmp_path / "good", **kwargs)
    bad = evaluate_mot(truth, switched, work_dir=tmp_path / "bad", **kwargs)
    assert good["status"] == bad["status"] == "evaluated"
    assert good["IDSW"] == 0
    assert bad["IDSW"] == 1
    assert good["HOTA"] > bad["HOTA"]
    assert good["MOTA"] > bad["MOTA"]
    without_ids = evaluate_mot([box(track_id=None)], perfect, work_dir=tmp_path / "noid", **kwargs)
    assert without_ids["status"] == "not_evaluated"
    assert without_ids["reason"] == "missing_identity_ground_truth"
