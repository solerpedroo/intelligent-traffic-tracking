"""Geometry in original pixel coordinates, with finite segment intersection."""

from dataclasses import dataclass
from math import hypot


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def subtract(a, b):
    return a[0] - b[0], a[1] - b[1]


def bottom_center(box):
    x1, _, x2, y2 = box
    return (x1 + x2) / 2, y2


@dataclass(frozen=True)
class PixelLine:
    line_id: str
    start: tuple[float, float]
    end: tuple[float, float]

    @classmethod
    def from_config(cls, line, width, height):
        # Continuous image plane [0,width] x [0,height], not display pixel indices.
        return cls(
            line.line_id,
            (line.start[0] * width, line.start[1] * height),
            (line.end[0] * width, line.end[1] * height),
        )

    def signed_distance(self, point):
        delta = subtract(self.end, self.start)
        return cross(delta, subtract(point, self.start)) / hypot(*delta)

    def intersection(self, previous, current):
        """Finite movement against finite line, endpoints inclusive, collinear excluded."""
        move, line = subtract(current, previous), subtract(self.end, self.start)
        denominator = cross(move, line)
        if abs(denominator) <= 1e-12 * max(1.0, hypot(*move) * hypot(*line)):
            return None
        offset = subtract(self.start, previous)
        t, u = cross(offset, line) / denominator, cross(offset, move) / denominator
        if -1e-10 <= t <= 1 + 1e-10 and -1e-10 <= u <= 1 + 1e-10:
            return previous[0] + t * move[0], previous[1] + t * move[1]
        return None
