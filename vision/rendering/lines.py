"""Finite line overlays and directional totals on the original image plane."""

import cv2


def render_lines(pixels, lines, summary):
    output = pixels.copy()
    height, width = output.shape[:2]

    def display(point):
        return max(0, min(width - 1, round(point[0]))), max(0, min(height - 1, round(point[1])))

    for line in lines:
        start, end = display(line.start), display(line.end)
        cv2.arrowedLine(output, start, end, (0, 255, 255), 2, cv2.LINE_AA, tipLength=0.03)
        totals = {
            r["direction"]: r["count"]
            for r in summary["by_line_direction"]
            if r["line_id"] == line.line_id
        }
        label = f"{line.line_id} A>B:{totals['A_TO_B']} B>A:{totals['B_TO_A']}"
        cv2.putText(
            output,
            label,
            (start[0], max(14, start[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            output,
            label,
            (start[0], max(14, start[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return output
