"""Versioned foundation configuration; adapters extend it in their own waves."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from vision.contracts.base import Contract, Identifier, Seconds


class ProcessingConfig(Contract):
    """Empty catalog means model IDs are unconfigured, never placeholder checkpoints.

    Model-specific thresholds and geometry schemas are added alongside their
    validated adapters in Waves 2–5. Baseline sampling is intentionally fixed.
    """

    schema_version: Literal["1.0"] = "1.0"
    video_id: Identifier
    detector_model_id: Identifier | None = None
    tracker_config_id: Identifier | None = None
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
        return self
