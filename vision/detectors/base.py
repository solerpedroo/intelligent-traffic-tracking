"""Normalized detections and timings, independent of a model framework."""

from dataclasses import dataclass
from typing import Protocol

from numpy.typing import NDArray

from vision.contracts import Detection
from vision.contracts.run import ModelReference


@dataclass(frozen=True, slots=True)
class DetectionBatch:
    detections: tuple[Detection, ...]
    preprocessing_ms: float
    predict_ms: float
    postprocessing_ms: float
    inference_ms: float


class DetectorAdapter(Protocol):
    reference: ModelReference
    class_names: dict[int, str]
    warmup_ms: float
    load_ms: float

    def warm_up(self, pixels: NDArray) -> None: ...

    def detect(self, pixels: NDArray) -> DetectionBatch: ...
