"""Canonical ground truth. Frame indexes stay zero-based until a converter asks otherwise."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from vision.contracts.base import Contract, Identifier, NonNegativeInt, Seconds

Direction = Literal["A_TO_B", "B_TO_A"]
SplitName = Literal["development", "validation", "test"]
LabelKind = Literal["detection", "mot", "counting"]


class GroundTruthBox(Contract):
    frame_index: NonNegativeInt
    class_id: NonNegativeInt
    bbox_xyxy: tuple[float, float, float, float]
    track_id: NonNegativeInt | None = None
    ignore: bool = False

    @model_validator(mode="after")
    def positive_box(self) -> Self:
        x1, y1, x2, y2 = self.bbox_xyxy
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox width and height must be positive")
        return self


class GroundTruthEvent(Contract):
    """Inclusive annotation window on the original media clock."""

    line_id: Identifier
    class_id: NonNegativeInt
    direction: Direction
    start_s: Seconds
    end_s: Seconds

    @model_validator(mode="after")
    def ordered_window(self) -> Self:
        if self.end_s < self.start_s:
            raise ValueError("event end_s cannot precede start_s")
        return self


class GroundTruthSequence(Contract):
    schema_version: Literal["1.0"] = "1.0"
    sequence_id: Identifier
    split: SplitName
    video_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    boxes: tuple[GroundTruthBox, ...] = ()
    events: tuple[GroundTruthEvent, ...] = ()

    @model_validator(mode="after")
    def unique_boxes_per_frame(self) -> Self:
        seen = set()
        for box in self.boxes:
            if box.ignore or box.track_id is None:
                continue
            key = (box.frame_index, box.track_id)
            if key in seen:
                raise ValueError("A track id cannot appear twice in the same frame")
            seen.add(key)
        return self


class SequenceSlot(Contract):
    sequence_id: Identifier
    split: SplitName
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")] | None = None
    labels: tuple[LabelKind, ...] = ()

    @model_validator(mode="after")
    def unique_labels(self) -> Self:
        if len(set(self.labels)) != len(self.labels):
            raise ValueError("labels must be unique")
        return self


class SplitRegistry(Contract):
    schema_version: Literal["1.0"] = "1.0"
    test_split_frozen: bool
    sequences: tuple[SequenceSlot, ...]

    @model_validator(mode="after")
    def unique_sequences(self) -> Self:
        ids = [item.sequence_id for item in self.sequences]
        if len(ids) != len(set(ids)):
            raise ValueError("sequence ids must be unique")
        return self


def events_from_frame_intervals(events, fps: float) -> tuple[GroundTruthEvent, ...]:
    """Map inclusive frame indexes with an explicit CFR. This does not infer VFR time."""
    if isinstance(fps, bool) or not isinstance(fps, (int, float)) or fps <= 0:
        raise ValueError("fps must be a positive number supplied by the annotation")
    converted = []
    for event in events:
        start, end = event["crossing_frame_interval"]
        converted.append(
            GroundTruthEvent(
                line_id=event["line_id"],
                class_id=event["class_id"],
                direction=event["direction"],
                start_s=float(start) / float(fps),
                end_s=float(end) / float(fps),
            )
        )
    return tuple(converted)
