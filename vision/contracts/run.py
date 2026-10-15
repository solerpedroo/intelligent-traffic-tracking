"""Reproducibility and progress snapshots; no job execution is implemented here."""

from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from vision.contracts.base import Contract, Identifier, NonNegativeInt, Sha256
from vision.contracts.config import ProcessingConfig

RunState = Literal["queued", "running", "completed", "failed", "cancelled"]


class SoftwareVersion(Contract):
    name: Identifier
    version: Annotated[str, Field(min_length=1)]


class ModelReference(Contract):
    model_id: Identifier
    checkpoint_sha256: Sha256
    implementation_version: Annotated[str, Field(min_length=1)]


class RunManifest(Contract):
    schema_version: Literal["1.0"] = "1.0"
    run_id: Identifier
    video_id: Identifier
    input_sha256: Sha256
    config: ProcessingConfig
    started_at: AwareDatetime
    finished_at: AwareDatetime | None = None
    git_commit: Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")] | None
    git_dirty: bool
    seed: NonNegativeInt | None
    hardware: Annotated[str, Field(min_length=1)]
    software: tuple[SoftwareVersion, ...]
    detector: ModelReference | None = None

    @model_validator(mode="after")
    def validate_snapshot(self) -> Self:
        if self.config.video_id != self.video_id:
            raise ValueError("manifest and config must refer to the same video_id")
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        names = [item.name for item in self.software]
        if len(names) != len(set(names)):
            raise ValueError("software names must be unique")
        if self.detector is not None and self.detector.model_id != self.config.detector_model_id:
            raise ValueError("detector must match the configured model")
        return self


class RunProgress(Contract):
    state: RunState = "queued"
    processed_frames: NonNegativeInt = 0
    total_frames: NonNegativeInt | None = None
    stage: Identifier = "queued"
    error: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def validate_progress(self) -> Self:
        if self.total_frames is not None and self.processed_frames > self.total_frames:
            raise ValueError("processed_frames cannot exceed total_frames")
        if self.state == "failed" and self.error is None:
            raise ValueError("failed progress requires an error")
        if self.state != "failed" and self.error is not None:
            raise ValueError("error is only allowed for failed progress")
        if (
            self.state == "completed"
            and self.total_frames is not None
            and self.processed_frames != self.total_frames
        ):
            raise ValueError("completed progress must account for all expected frames")
        return self
