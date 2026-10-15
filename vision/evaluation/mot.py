"""Per-class TrackEval scores. MOTChallenge pedestrian id 1 is only the file encoding."""

import contextlib
import importlib.util
import io
from pathlib import Path

import numpy as np

from vision.datasets.trackeval_export import write_sequence


def _plain(value):
    if isinstance(value, np.ndarray):
        if value.size == 0:
            return None
        return float(np.mean(value))
    if isinstance(value, np.generic):
        return value.item()
    return value


def _metric(sequence_metrics, name, field):
    metric = sequence_metrics.get(name, {})
    if field not in metric:
        return None
    value = _plain(metric[field])
    if isinstance(value, float):
        return value
    if isinstance(value, int):
        return value
    return None


def evaluate_mot(
    ground_truth,
    predictions,
    protocol,
    work_dir: Path,
    *,
    class_id: int,
    sequence_id: str,
    frame_rate: float,
    width: int,
    height: int,
):
    """Score one class. Other classes are omitted rather than marked as distractors."""
    if class_id in protocol.ignored_class_ids:
        return {"status": "not_evaluated", "reason": "ignored_class", "class_id": class_id}
    truth = [box for box in ground_truth if box.class_id == class_id and not box.ignore]
    preds = [box for box in predictions if box["class_id"] == class_id]
    if not truth:
        return {
            "status": "not_evaluated",
            "reason": "no_ground_truth_for_class",
            "class_id": class_id,
        }
    if any(box.track_id is None for box in truth):
        return {
            "status": "not_evaluated",
            "reason": "missing_identity_ground_truth",
            "class_id": class_id,
        }
    if any(box["track_id"] is None for box in preds):
        return {
            "status": "not_evaluated",
            "reason": "missing_prediction_identity",
            "class_id": class_id,
        }
    if importlib.util.find_spec("trackeval") is None:
        return {
            "status": "not_evaluated",
            "reason": "missing_evaluation_extra",
            "class_id": class_id,
        }
    with contextlib.redirect_stdout(io.StringIO()):
        import trackeval

    exported = write_sequence(
        work_dir / f"class-{class_id}",
        sequence_id,
        [
            {
                "frame_index": box.frame_index,
                "track_id": box.track_id,
                "bbox_xyxy": box.bbox_xyxy,
            }
            for box in truth
        ],
        preds,
        frame_rate=frame_rate,
        width=width,
        height=height,
    )
    eval_config = trackeval.Evaluator.get_default_eval_config()
    for key, value in {
        "USE_PARALLEL": False,
        "PRINT_RESULTS": False,
        "PRINT_ONLY_COMBINED": False,
        "PRINT_CONFIG": False,
        "OUTPUT_SUMMARY": False,
        "OUTPUT_DETAILED": False,
        "PLOT_CURVES": False,
        "TIME_PROGRESS": False,
    }.items():
        if key in eval_config:
            eval_config[key] = value
    dataset_config = trackeval.datasets.MotChallenge2DBox.get_default_dataset_config()
    dataset_config.update(
        {
            "GT_FOLDER": str(exported["gt_folder"]),
            "TRACKERS_FOLDER": str(exported["trackers_folder"]),
            "OUTPUT_FOLDER": str(work_dir / f"class-{class_id}" / "output"),
            "TRACKERS_TO_EVAL": ["baseline"],
            "CLASSES_TO_EVAL": ["pedestrian"],
            "BENCHMARK": "MOT17",
            "SPLIT_TO_EVAL": "train",
            "DO_PREPROC": False,
            "SKIP_SPLIT_FOL": True,
            "PRINT_CONFIG": False,
            "SEQ_INFO": {sequence_id: exported["seq_length"]},
        }
    )
    metrics_config = {
        "METRICS": ["HOTA", "CLEAR", "Identity"],
        "THRESHOLD": protocol.mot_similarity_iou,
        "PRINT_CONFIG": False,
    }
    dataset = trackeval.datasets.MotChallenge2DBox(dataset_config)
    metrics = [
        trackeval.metrics.HOTA(metrics_config),
        trackeval.metrics.CLEAR(metrics_config),
        trackeval.metrics.Identity(metrics_config),
    ]
    with contextlib.redirect_stdout(io.StringIO()):
        results, _messages = trackeval.Evaluator(eval_config).evaluate([dataset], metrics)
    sequence = results["MotChallenge2DBox"]["baseline"][sequence_id]["pedestrian"]
    return {
        "status": "evaluated",
        "reason": None,
        "class_id": class_id,
        "encoding": "class_mapped_to_motchallenge_pedestrian_id_1",
        "preprocessing": protocol.mot_preprocessing,
        "similarity_iou": protocol.mot_similarity_iou,
        "HOTA": _metric(sequence, "HOTA", "HOTA"),
        "MOTA": _metric(sequence, "CLEAR", "MOTA"),
        "IDF1": _metric(sequence, "Identity", "IDF1"),
        "IDSW": _metric(sequence, "CLEAR", "IDSW"),
        "note": "Not a MOTChallenge leaderboard score. Distractor preprocessing is disabled.",
    }
