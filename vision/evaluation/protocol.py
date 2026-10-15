"""Frozen scoring rules. Changing the committed JSON is a protocol change."""

from decimal import Decimal
from typing import Literal, Self

from pydantic import model_validator

from vision.contracts.base import Contract, NonNegativeInt


def iou_thresholds(start=0.5, stop=0.95, step=0.05) -> tuple[float, ...]:
    values = []
    cursor = Decimal(str(start))
    end = Decimal(str(stop))
    increment = Decimal(str(step))
    while cursor <= end:
        values.append(float(cursor))
        cursor += increment
    return tuple(values)


class EvaluationProtocol(Contract):
    schema_version: Literal["1.0"] = "1.0"
    detection_iou_start: float = 0.5
    detection_iou_stop: float = 0.95
    detection_iou_step: float = 0.05
    counting_tolerance_s: float = 0.5
    ignored_class_ids: tuple[NonNegativeInt, ...] = ()
    mot_similarity_iou: float = 0.5
    mot_preprocessing: Literal["disabled"] = "disabled"
    average_precision: Literal["coco_101_point"] = "coco_101_point"

    @model_validator(mode="after")
    def frozen_shape(self) -> Self:
        if self.detection_iou_step <= 0 or self.detection_iou_start > self.detection_iou_stop:
            raise ValueError("IoU thresholds must increase from start to stop")
        if not 0 < self.counting_tolerance_s <= 5:
            raise ValueError("counting tolerance must be in (0, 5] seconds")
        if not 0 < self.mot_similarity_iou <= 1:
            raise ValueError("MOT similarity IoU must be in (0, 1]")
        if len(set(self.ignored_class_ids)) != len(self.ignored_class_ids):
            raise ValueError("ignored class ids must be unique")
        return self

    @property
    def detection_iou_thresholds(self) -> tuple[float, ...]:
        return iou_thresholds(
            self.detection_iou_start, self.detection_iou_stop, self.detection_iou_step
        )
