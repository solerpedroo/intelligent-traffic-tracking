"""ROI outlines and observed occupancy, independent of detector drawing thresholds."""

import cv2
import numpy as np


def render_zones(pixels, zones, occupancy):
    output = pixels.copy()
    height, width = output.shape[:2]
    for zone in zones:
        vertices = np.asarray(
            [
                (min(width - 1, round(x * width)), min(height - 1, round(y * height)))
                for x, y in zone.vertices
            ],
            dtype=np.int32,
        )
        cv2.polylines(output, [vertices], True, (220, 130, 255), 2, cv2.LINE_AA)
        count = sum(n for (zone_id, _), n in occupancy.items() if zone_id == zone.zone_id)
        label = f"{zone.zone_id} observed:{count}"
        anchor = (int(vertices[:, 0].min()), max(15, int(vertices[:, 1].min()) - 8))
        for color, thickness in (((0, 0, 0), 3), ((220, 130, 255), 1)):
            cv2.putText(
                output, label, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, thickness, cv2.LINE_AA
            )
    return output
