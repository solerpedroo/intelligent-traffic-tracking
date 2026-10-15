"""Public internal data contracts, independent of transport and model libraries."""

from vision.contracts.config import ProcessingConfig
from vision.contracts.observations import (
    CrossingEvent,
    Detection,
    FramePacket,
    Track,
    TrackObservation,
    ZoneEvent,
)
from vision.contracts.run import ModelReference, RunManifest, RunProgress, SoftwareVersion

__all__ = [
    "CrossingEvent",
    "Detection",
    "FramePacket",
    "ModelReference",
    "ProcessingConfig",
    "RunManifest",
    "RunProgress",
    "SoftwareVersion",
    "Track",
    "TrackObservation",
    "ZoneEvent",
]
