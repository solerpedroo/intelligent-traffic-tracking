"""MOTChallenge files. Internal frame 0 becomes MOTChallenge frame 1, gaps included."""

import configparser
import csv
from pathlib import Path

from vision.contracts.errors import VisionError

MOT_CLASS_ID = 1


def mot_frame(frame_index: int) -> int:
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or frame_index < 0:
        raise VisionError("invalid_frame", "frame_index must be a non-negative integer")
    return frame_index + 1


def _row(frame_index, track_id, bbox, confidence):
    if isinstance(track_id, bool) or not isinstance(track_id, int) or track_id <= 0:
        raise VisionError("invalid_track_id", "MOTChallenge ids must be positive")
    x1, y1, x2, y2 = bbox
    return [
        mot_frame(frame_index),
        track_id,
        x1,
        y1,
        x2 - x1,
        y2 - y1,
        confidence,
        MOT_CLASS_ID,
        1,
    ]


def write_sequence(
    directory: Path,
    sequence_id: str,
    gt_boxes,
    pred_boxes,
    *,
    frame_rate: float,
    width: int,
    height: int,
):
    """Write one class already filtered by the caller. Class column is pedestrian id 1."""
    if not gt_boxes:
        raise VisionError("empty_ground_truth", "TrackEval export needs one ground-truth box")
    gt_file = directory / "gt" / sequence_id / "gt" / "gt.txt"
    pred_file = directory / "trackers" / "baseline" / "data" / f"{sequence_id}.txt"
    gt_file.parent.mkdir(parents=True, exist_ok=False)
    pred_file.parent.mkdir(parents=True)
    indexes = [box["frame_index"] for box in gt_boxes]
    indexes.extend(box["frame_index"] for box in pred_boxes)
    seq_length = max(indexes) + 1
    with gt_file.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(
            _row(box["frame_index"], box["track_id"], box["bbox_xyxy"], 1) for box in gt_boxes
        )
    with pred_file.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(
            _row(box["frame_index"], box["track_id"], box["bbox_xyxy"], box["confidence"])
            for box in pred_boxes
        )
    parser = configparser.ConfigParser()
    parser["Sequence"] = {
        "name": sequence_id,
        "imDir": "img1",
        "frameRate": str(frame_rate),
        "seqLength": str(seq_length),
        "imWidth": str(width),
        "imHeight": str(height),
        "imExt": ".jpg",
    }
    with (directory / "gt" / sequence_id / "seqinfo.ini").open("w", encoding="utf-8") as handle:
        parser.write(handle)
    return {
        "gt": gt_file,
        "predictions": pred_file,
        "seq_length": seq_length,
        "gt_folder": directory / "gt",
        "trackers_folder": directory / "trackers",
    }
