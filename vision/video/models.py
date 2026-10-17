"""Metadata is reported by the container, not a claim that all frames decode."""

from typing import Annotated, Literal

from pydantic import Field

from vision.contracts.base import Contract, NonNegativeInt, Seconds


class VideoLimits(Contract):
    max_bytes: Annotated[int, Field(gt=0)] = 4 * 1024 * 1024 * 1024
    max_duration_s: Annotated[float, Field(gt=0)] = 45 * 60
    max_pixels: Annotated[int, Field(gt=0)] = 1920 * 1080
    max_frames: Annotated[int, Field(gt=0)] = 45 * 60 * 60


class VideoMetadata(Contract):
    schema_version: Literal["1.0"] = "1.0"
    filename: str
    size_bytes: NonNegativeInt
    container: str
    codec: str
    width: Annotated[int, Field(gt=0)]
    height: Annotated[int, Field(gt=0)]
    reported_fps: Annotated[float, Field(gt=0)] | None
    reported_frames: NonNegativeInt | None
    reported_duration_s: Seconds | None
    stream_time_base: tuple[int, int]
    stream_start_s: float | None
    duration_source: Literal["stream", "container", "unknown"]
    validation: Literal["headers_only"] = "headers_only"
