"""Versioned foundation configuration; adapters extend it in their own waves."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from vision.contracts.base import Confidence, Contract, Identifier, Seconds
from vision.contracts.counting import CountingConfig


class DetectorConfig(Contract):
    """Baseline controls; lower detection threshold is independent of drawing."""

    confidence: Confidence = 0.1
    iou: Confidence = 0.7
    image_size: Annotated[int, Field(ge=320, le=1280, multiple_of=32)] = 640
    classes: tuple[str, ...] = ("person", "bicycle", "car", "motorcycle", "bus", "truck")
    device: Annotated[str, Field(pattern=r"^(cpu|cuda:[0-9]+)$")] = "cpu"
    visualization_confidence: Confidence = 0.25
    warmup_frames: Annotated[int, Field(ge=1, le=10)] = 2
    threads: Annotated[int, Field(ge=1, le=16)] = 1
    max_detections: Annotated[int, Field(ge=1, le=1000)] = 300
    seed: Annotated[int, Field(ge=0, le=2**32 - 1)] = 0

    @model_validator(mode="after")
    def validate_classes(self) -> Self:
        if not self.classes or len(set(self.classes)) != len(self.classes):
            raise ValueError("classes must be non-empty and unique")
        return self


class TrackerConfig(Contract):
    """ByteTrack controls; buffer counts update calls, never seconds or nominal FPS."""

    track_high_thresh: Confidence = 0.25
    track_low_thresh: Confidence = 0.1
    new_track_thresh: Confidence = 0.25
    track_buffer: Annotated[int, Field(ge=1, le=300)] = 30
    match_thresh: Annotated[float, Field(gt=0, le=1)] = 0.8
    fuse_score: bool = True
    min_observations: Annotated[int, Field(ge=1, le=1000)] = 3
    history_points: Annotated[int, Field(ge=2, le=1000)] = 64
    max_live_tracks: Annotated[int, Field(ge=1, le=10000)] = 4000

    @model_validator(mode="after")
    def validate_thresholds(self) -> Self:
        if not self.track_low_thresh < self.track_high_thresh <= self.new_track_thresh:
            raise ValueError("Require low < high <= new track threshold")
        return self


class ProcessingConfig(Contract):
    """Resolved run controls; model and tracker IDs are checked against the catalog.

    Baseline sampling is fixed; geometry enters alongside its validated adapters.
    """

    schema_version: Literal["1.0"] = "1.0"
    video_id: Identifier
    detector_model_id: Identifier | None = None
    detector: DetectorConfig = Field(default_factory=DetectorConfig)
    tracker_config_id: Identifier | None = None
    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    counting: CountingConfig = Field(default_factory=CountingConfig)
    frame_stride: Annotated[int, Field(ge=1, le=1)] = 1
    render_annotated_video: bool = True
    start_s: Seconds = 0.0
    end_s: Seconds | None = None

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.end_s is not None and self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        if self.tracker_config_id is not None and self.detector_model_id is None:
            raise ValueError("tracker_config_id requires detector_model_id")
        if self.counting.lines and self.tracker_config_id is None:
            raise ValueError("Counting lines require tracker_config_id")
        if self.tracker_config_id and self.detector.confidence > self.tracker.track_low_thresh:
            raise ValueError("Detector confidence must be <= tracker low threshold")
        return self
