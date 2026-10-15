"""Observed IDs and bounded trails; missing frames are never connected as evidence."""

import cv2
import numpy as np

from vision.rendering.detections import render_detections


def render_tracks(pixels, tracks, histories, class_names, threshold):
    observed = tuple(t for t in tracks if t.state == "observed")
    names = {t.class_id: class_names[t.class_id] for t in observed}
    output, drawn = render_detections(pixels, observed, names, threshold)
    for track in observed:
        if track.confidence < threshold:
            continue
        x1, y1, _, _ = track.bbox_xyxy
        cv2.putText(
            output,
            f"ID {track.track_id}",
            (round(x1), max(25, round(y1) + 16)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (80, 255, 160),
            1,
            cv2.LINE_AA,
        )
        points = histories[track.track_id].points
        for previous, current in zip(points, list(points)[1:], strict=False):
            if current[0] == previous[0] + 1:
                a, b = np.rint(previous[2:]).astype(int), np.rint(current[2:]).astype(int)
                cv2.line(output, tuple(a), tuple(b), (80, 255, 160), 2, cv2.LINE_AA)
    return output, drawn
