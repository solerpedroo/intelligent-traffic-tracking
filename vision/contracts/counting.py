"""Normalized finite lines and auditable line-crossing controls."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from vision.contracts.base import Contract, Identifier

UnitCoordinate = Annotated[float, Field(ge=0, le=1)]
Point = tuple[UnitCoordinate, UnitCoordinate]


class LineConfig(Contract):
    line_id: Identifier
    start: Point
    end: Point

    @model_validator(mode="after")
    def nonzero(self) -> Self:
        if self.start == self.end:
            raise ValueError("Line endpoints must be distinct")
        return self


class CountingConfig(Contract):
    lines: Annotated[tuple[LineConfig, ...], Field(max_length=16)] = ()
    hysteresis_px: Annotated[float, Field(ge=0, le=100)] = 3.0
    min_observations: Annotated[int, Field(ge=2, le=1000)] = 3
    stable_observations: Annotated[int, Field(ge=1, le=30)] = 2
    max_gap_frames: Annotated[int, Field(ge=1, le=300)] = 1
    max_gap_s: Annotated[float, Field(gt=0, le=30)] = 0.5
    window_s: Annotated[float, Field(ge=0.1, le=3600)] = 60.0

    @model_validator(mode="after")
    def unique_lines(self) -> Self:
        ids = [line.line_id for line in self.lines]
        if len(ids) != len(set(ids)):
            raise ValueError("Line IDs must be unique")
        return self
