"""Read pipeline CSV exports without treating missing files as zero scores."""

import csv
from pathlib import Path

from vision.contracts.errors import VisionError


def _float(value, name):
    if value is None or value == "":
        raise VisionError("invalid_prediction", f"{name} is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise VisionError("invalid_prediction", f"{name} must be numeric") from error
    if number != number or number in {float("inf"), float("-inf")}:
        raise VisionError("invalid_prediction", f"{name} must be finite")
    return number


def _int(value, name):
    number = _float(value, name)
    if int(number) != number:
        raise VisionError("invalid_prediction", f"{name} must be an integer")
    return int(number)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_predictions(directory: Path) -> dict:
    directory = directory.expanduser().resolve()
    loaded = {"directory": str(directory), "missing": []}
    for name, key in (
        ("detections.csv", "detections"),
        ("tracks.csv", "tracks"),
        ("crossing_events.csv", "events"),
        ("timings.csv", "timings"),
        ("summary.json", "summary"),
    ):
        path = directory / name
        if not path.is_file():
            loaded["missing"].append(name)
            loaded[key] = None
            continue
        if name.endswith(".json"):
            import json

            loaded[key] = json.loads(path.read_text(encoding="utf-8"))
        else:
            loaded[key] = read_csv(path)
    return loaded


def detection_boxes(rows):
    boxes = []
    for row in rows:
        boxes.append(
            {
                "frame_index": _int(row["frame_index"], "frame_index"),
                "class_id": _int(row["class_id"], "class_id"),
                "confidence": _float(row["confidence"], "confidence"),
                "bbox_xyxy": (
                    _float(row["x1"], "x1"),
                    _float(row["y1"], "y1"),
                    _float(row["x2"], "x2"),
                    _float(row["y2"], "y2"),
                ),
            }
        )
    return tuple(boxes)


def observed_tracks(rows):
    tracks = []
    excluded = 0
    for row in rows:
        if row["state"] != "observed":
            excluded += 1
            continue
        tracks.append(
            {
                "frame_index": _int(row["frame_index"], "frame_index"),
                "track_id": _int(row["track_id"], "track_id"),
                "class_id": _int(row["class_id"], "class_id"),
                "confidence": _float(row["confidence"], "confidence"),
                "bbox_xyxy": (
                    _float(row["x1"], "x1"),
                    _float(row["y1"], "y1"),
                    _float(row["x2"], "x2"),
                    _float(row["y2"], "y2"),
                ),
            }
        )
    return tuple(tracks), excluded


def crossing_events(rows):
    events = []
    for row in rows:
        events.append(
            {
                "line_id": row["line_id"],
                "class_id": _int(row["class_id"], "class_id"),
                "direction": row["direction"],
                "timestamp_s": _float(row["timestamp_s"], "timestamp_s"),
            }
        )
    return tuple(events)
