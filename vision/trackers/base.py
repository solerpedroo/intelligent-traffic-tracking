"""Temporal adapter contract independent of model frameworks."""

from typing import Protocol

from vision.contracts import Detection, FramePacket, Track


class TrackerAdapter(Protocol):
    def reset(self) -> None: ...

    def update(self, frame: FramePacket, detections: tuple[Detection, ...]) -> tuple[Track, ...]:
        """Advance exactly once per consecutive frame, including empty detections."""
        ...
