"""Render original-coordinate boxes on a copy of the supplied BGR frame."""

import cv2


def render_detections(pixels, detections, class_names, threshold):
    output = pixels.copy()
    height, width = output.shape[:2]
    drawn = 0
    for detection in detections:
        if detection.confidence < threshold:
            continue
        x1, y1, x2, y2 = detection.bbox_xyxy
        start = (max(0, min(width - 1, round(x1))), max(0, min(height - 1, round(y1))))
        end = (max(0, min(width - 1, round(x2))), max(0, min(height - 1, round(y2))))
        label = f"{class_names[detection.class_id]} {detection.confidence:.2f}"
        cv2.rectangle(output, start, end, (255, 178, 80), 2)
        cv2.putText(
            output,
            label,
            (start[0], max(12, start[1] - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (255, 220, 160),
            1,
            cv2.LINE_AA,
        )
        drawn += 1
    return output, drawn
