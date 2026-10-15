"""Observations in original image coordinates and original media time."""

from dataclasses import dataclass, field
from math import isfinite
from typing import Literal, Self

import numpy as np
from numpy.typing import NDArray
from pydantic import model_validator

from vision.contracts.base import Confidence, Contract, Identifier, NonNegativeInt, Seconds


@dataclass(frozen=True, slots=True, eq=False)
class FramePacket:
    """Internal BGR uint8 H×W×3 frame; array is borrowed, callers must not mutate it.

    Metadata is frozen; pixel memory is not copied or made immutable. This is not
    a JSON contract. The frame index and timestamp refer to the original video.
    """

    frame_index: int
    timestamp_s: float
    pixels: NDArray[np.uint8] = field(repr=False)
    timestamp_source: Literal["pts", "fps_fallback"] = "pts"
    duration_s: float | None = None

    def __post_init__(self) -> None:
        if type(self.frame_index) is not int or self.frame_index < 0:
            raise ValueError("frame_index must be a non-negative integer")
        if (
            isinstance(self.timestamp_s, bool)
            or not isinstance(self.timestamp_s, (int, float))
            or not isfinite(self.timestamp_s)
            or self.timestamp_s < 0
        ):
            raise ValueError("timestamp_s must be finite and non-negative")
        if self.timestamp_source not in ("pts", "fps_fallback"):
            raise ValueError("timestamp_source must be pts or fps_fallback")
        if self.duration_s is not None and (
            isinstance(self.duration_s, bool)
            or not isinstance(self.duration_s, (int, float))
            or not isfinite(self.duration_s)
            or self.duration_s <= 0
        ):
            raise ValueError("duration_s must be positive and finite when available")
        if not isinstance(self.pixels, np.ndarray) or self.pixels.dtype != np.uint8:
            raise ValueError("pixels must be a uint8 NumPy array")
        if self.pixels.ndim != 3 or self.pixels.shape[2] != 3 or 0 in self.pixels.shape:
            raise ValueError("pixels must have a non-empty H×W×3 shape")
        if not self.pixels.flags.c_contiguous:
            raise ValueError("pixels must be C-contiguous")


class BoundingBox(Contract):
    """Finite xyxy pixel coordinates. Image-bound clipping is an adapter concern."""

    bbox_xyxy: tuple[float, float, float, float]

    @model_validator(mode="after")
    def validate_extent(self) -> Self:
        x1, y1, x2, y2 = self.bbox_xyxy
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox_xyxy must have positive width and height")
        return self


class Detection(BoundingBox):
    class_id: NonNegativeInt
    confidence: Confidence


class Track(BoundingBox):
    """ID is local to a run; state distinguishes observations from predictions."""

    track_id: NonNegativeInt
    class_id: NonNegativeInt
    confidence: Confidence | None
    state: Literal["observed", "predicted", "lost"] = "observed"


class TrackObservation(Contract):
    run_id: Identifier
    video_id: Identifier
    frame_index: NonNegativeInt
    timestamp_s: Seconds
    track: Track


class CrossingEvent(Contract):
    run_id: Identifier
    video_id: Identifier
    frame_index: NonNegativeInt
    timestamp_s: Seconds
    track_id: NonNegativeInt
    class_id: NonNegativeInt
    line_id: Identifier
    direction: Literal["A_TO_B", "B_TO_A"]
    event_type: Literal["line_crossing"] = "line_crossing"
    evidence_start_frame: NonNegativeInt | None = None
    evidence_start_s: Seconds | None = None
    intersection_xy: tuple[float, float] | None = None
    observed_count: NonNegativeInt | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> Self:
        fields = (
            self.evidence_start_frame,
            self.evidence_start_s,
            self.intersection_xy,
            self.observed_count,
        )
        if all(item is None for item in fields):
            return self  # Preserve the minimal event contract from Wave 0.
        if any(item is None for item in fields):
            raise ValueError("Crossing evidence must be complete when supplied")
        if (
            self.evidence_start_frame >= self.frame_index
            or self.evidence_start_s >= self.timestamp_s
            or self.observed_count < 2
        ):
            raise ValueError(
                "Crossing evidence must precede confirmation and have >=2 observations"
            )
        return self


class ZoneEvent(Contract):
    """Lost observations and media boundaries are not geometric exits."""

    run_id: Identifier
    video_id: Identifier
    frame_index: NonNegativeInt
    timestamp_s: Seconds
    track_id: NonNegativeInt
    class_id: NonNegativeInt
    zone_id: Identifier
    event_type: Literal["zone_enter", "zone_exit", "observation_lost", "boundary_censored"]
