"""Explicit letterbox with invertible resize/padding metadata."""

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class LetterboxTransform:
    width: int
    height: int
    size: int
    resized_width: int
    resized_height: int
    left: int
    top: int

    @classmethod
    def for_shape(cls, height: int, width: int, size: int) -> "LetterboxTransform":
        if min(height, width, size) <= 0:
            raise ValueError("Image dimensions must be positive")
        gain = min(size / width, size / height)
        resized_width, resized_height = max(1, round(width * gain)), max(1, round(height * gain))
        return cls(
            width,
            height,
            size,
            resized_width,
            resized_height,
            (size - resized_width) // 2,
            (size - resized_height) // 2,
        )

    def apply(self, pixels: NDArray[np.uint8]) -> NDArray[np.uint8]:
        if pixels.dtype != np.uint8 or pixels.shape != (self.height, self.width, 3):
            raise ValueError("Expected an original-size BGR uint8 frame")
        resized = cv2.resize(
            pixels, (self.resized_width, self.resized_height), interpolation=cv2.INTER_LINEAR
        )
        return cv2.copyMakeBorder(
            resized,
            self.top,
            self.size - self.resized_height - self.top,
            self.left,
            self.size - self.resized_width - self.left,
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )

    def restore_boxes(self, boxes: NDArray) -> NDArray:
        boxes = np.asarray(boxes, dtype=np.float64).reshape(-1, 4).copy()
        if not np.isfinite(boxes).all():
            raise ValueError("Non-finite detector boxes")
        boxes[:, (0, 2)] = (boxes[:, (0, 2)] - self.left) / (self.resized_width / self.width)
        boxes[:, (1, 3)] = (boxes[:, (1, 3)] - self.top) / (self.resized_height / self.height)
        boxes[:, (0, 2)] = boxes[:, (0, 2)].clip(0, self.width)
        boxes[:, (1, 3)] = boxes[:, (1, 3)].clip(0, self.height)
        return boxes
