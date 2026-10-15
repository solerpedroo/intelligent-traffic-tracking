"""Normalized ROI and bounded observation heatmap configuration."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from vision.contracts.base import Contract, Identifier, NonNegativeInt, Seconds
from vision.contracts.counting import Point
from vision.geometry.polygons import validate_polygon


class ZoneConfig(Contract):
    zone_id: Identifier
    vertices: Annotated[tuple[Point, ...], Field(min_length=3, max_length=64)]

    @model_validator(mode="after")
    def simple_polygon(self) -> Self:
        validate_polygon(self.vertices)
        return self


class HeatmapConfig(Contract):
    enabled: bool = False
    class_ids: Annotated[tuple[NonNegativeInt, ...], Field(max_length=16)] = ()
    grid_width: Annotated[int, Field(ge=8, le=256)] = 128
    grid_height: Annotated[int, Field(ge=8, le=256)] = 72
    window_s: Annotated[float, Field(ge=1, le=3600)] = 60.0
    sigma_cells: Annotated[float, Field(ge=0, le=10)] = 1.0
    weighting: Literal["observations"] = "observations"

    @model_validator(mode="after")
    def unique_classes(self) -> Self:
        if len(set(self.class_ids)) != len(self.class_ids):
            raise ValueError("Heatmap class IDs must be unique")
        return self


class AnalyticsConfig(Contract):
    zones: Annotated[tuple[ZoneConfig, ...], Field(max_length=16)] = ()
    max_gap_s: Annotated[float, Field(gt=0, le=30)] = 0.5
    heatmap: HeatmapConfig = Field(default_factory=HeatmapConfig)

    @model_validator(mode="after")
    def unique_zones(self) -> Self:
        ids = [zone.zone_id for zone in self.zones]
        if len(set(ids)) != len(ids):
            raise ValueError("Zone IDs must be unique")
        return self


class ZoneVisit(Contract):
    run_id: Identifier
    video_id: Identifier
    visit_id: NonNegativeInt
    track_id: NonNegativeInt
    class_id: NonNegativeInt
    zone_id: Identifier
    first_inside_frame: NonNegativeInt
    last_inside_frame: NonNegativeInt
    first_inside_s: Seconds
    last_inside_s: Seconds
    observed_dwell_s: Seconds
    observations: Annotated[int, Field(ge=1)]
    left_censored: bool
    right_censored: bool
    start_reason: str
    end_reason: Literal["zone_exit", "observation_lost", "selection_end"]
    closed_frame: NonNegativeInt
    closed_s: Seconds

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if not self.first_inside_frame <= self.last_inside_frame <= self.closed_frame:
            raise ValueError("Visit frames must be ordered")
        if not self.first_inside_s <= self.last_inside_s <= self.closed_s:
            raise ValueError("Visit timestamps must be ordered")
        if self.observed_dwell_s > self.last_inside_s - self.first_inside_s + 1e-9:
            raise ValueError("Observed dwell cannot exceed the observed span")
        return self
