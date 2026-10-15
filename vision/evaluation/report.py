"""Per-sequence report. Frozen-test claims require the committed split registry."""

import hashlib
import json

from vision.evaluation.counting import evaluate_counting
from vision.evaluation.detection import evaluate_detection
from vision.evaluation.mot import evaluate_mot
from vision.evaluation.performance import evaluate_performance


def block_reason(registry, sequence_id):
    if not registry.test_split_frozen:
        return "test_split_not_frozen"
    match = next((item for item in registry.sequences if item.sequence_id == sequence_id), None)
    if match is None:
        return "sequence_not_in_registry"
    if match.split != "test":
        return "sequence_not_in_frozen_test_split"
    if match.sha256 is None:
        return "missing_sequence_hash"
    return None


def protocol_sha256(protocol) -> str:
    payload = json.dumps(protocol.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _mean(values):
    numbers = [
        value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if not numbers:
        return None
    return sum(numbers) / len(numbers)


def aggregate_reports(reports):
    """Average only evaluated numbers. A missing metric is omitted, not inserted as zero."""
    maps = [
        item["detection"]["mean_average_precision_50_95"]
        for item in reports
        if item["detection"].get("status") == "evaluated"
    ]
    errors = [
        item["counting"]["absolute_error"]
        for item in reports
        if item["counting"].get("status") == "evaluated"
    ]
    return {
        "sequences": len(reports),
        "benchmark_sequences": sum(item["benchmark_eligible"] for item in reports),
        "mean_average_precision_50_95": _mean(maps),
        "mean_absolute_count_error": _mean(errors),
        "omitted_from_mean": "not_evaluated metrics are excluded, not treated as zero",
    }


def build_report(
    sequence,
    predictions,
    protocol,
    *,
    timings=None,
    summary=None,
    mot_dir=None,
    frame_rate=None,
    width=None,
    height=None,
    claim="development_not_benchmark",
):
    detection = evaluate_detection(predictions.get("detections") or [], sequence.boxes, protocol)
    counting = evaluate_counting(predictions.get("events") or [], sequence.events, protocol)
    if predictions.get("detections") is None:
        detection = {"status": "not_evaluated", "reason": "missing_detections"}
    if predictions.get("events") is None:
        counting = {"status": "not_evaluated", "reason": "missing_crossing_events"}
    mot = {"status": "not_evaluated", "reason": "missing_tracks"}
    if predictions.get("tracks") is not None:
        classes = sorted({box.class_id for box in sequence.boxes if not box.ignore})
        per_class = []
        if mot_dir is None or frame_rate is None or width is None or height is None:
            mot = {"status": "not_evaluated", "reason": "missing_mot_geometry"}
        else:
            for class_id in classes:
                per_class.append(
                    evaluate_mot(
                        sequence.boxes,
                        predictions["tracks"],
                        protocol,
                        mot_dir,
                        class_id=class_id,
                        sequence_id=sequence.sequence_id,
                        frame_rate=frame_rate,
                        width=width,
                        height=height,
                    )
                )
            evaluated = [item for item in per_class if item["status"] == "evaluated"]
            if evaluated:
                reason = None
            elif per_class:
                reason = per_class[0]["reason"]
            else:
                reason = "no_boxes"
            mot = {
                "status": "evaluated" if evaluated else "not_evaluated",
                "reason": reason,
                "by_class": per_class,
                "macro_hota": _mean(item.get("HOTA") for item in evaluated),
                "macro_idf1": _mean(item.get("IDF1") for item in evaluated),
                "macro_mota": _mean(item.get("MOTA") for item in evaluated),
                "id_switches": None
                if not evaluated
                else sum(int(item["IDSW"]) for item in evaluated if item.get("IDSW") is not None),
            }
    scales = {}
    for name in ("small", "medium", "large"):
        scales[name] = evaluate_detection(
            predictions.get("detections") or [], sequence.boxes, protocol, scale=name
        )
    return {
        "schema_version": "1.0",
        "sequence_id": sequence.sequence_id,
        "claim": claim,
        "benchmark_eligible": claim == "frozen_test_benchmark",
        "protocol_sha256": protocol_sha256(protocol),
        "video_sha256": sequence.video_sha256,
        "detection": detection,
        "detection_by_scale": scales,
        "counting": counting,
        "mot": mot,
        "performance": evaluate_performance(timings, summary),
    }
