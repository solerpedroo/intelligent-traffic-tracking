"""Adapter for the pinned, concrete Ultralytics ByteTrack implementation."""

import os
from importlib.metadata import PackageNotFoundError, version
from types import SimpleNamespace

import numpy as np

from vision.contracts import Detection, FramePacket, Track
from vision.contracts.config import TrackerConfig
from vision.contracts.errors import VisionError


class _Boxes:
    """Minimal NumPy results interface; no Torch conversion or image preprocessing."""

    def __init__(self, data):
        self.data = data
        self.conf = data[:, 4]
        self.cls = data[:, 5]
        self.xywh = data[:, :4].copy()
        self.xywh[:, :2] = (data[:, :2] + data[:, 2:4]) / 2
        self.xywh[:, 2:4] = data[:, 2:4] - data[:, :2]

    def __len__(self):
        return len(self.data)

    def __getitem__(self, index):
        return _Boxes(self.data[index])


class ByteTrackAdapter:
    """Class-agnostic association, class frozen at first detection for each local ID.

    Observed boxes are the matched input detection, not a Kalman extrapolation.
    Lost boxes are estimates with confidence=None and never trajectory points.
    Later entrants require the upstream second-frame confirmation.
    """

    def __init__(self, config: TrackerConfig):
        try:
            versions = (version("ultralytics-opencv-headless"), version("lap"))
        except PackageNotFoundError as error:
            raise VisionError(
                "missing_detector_extra", "Install the pinned detector extra"
            ) from error
        if versions != ("8.4.177", "0.5.13"):
            raise VisionError("tracker_version", "Install the pinned detector extra")
        os.environ["YOLO_AUTOINSTALL"] = "false"
        os.environ["YOLO_OFFLINE"] = "true"
        from ultralytics.trackers.basetrack import TrackState
        from ultralytics.trackers.byte_tracker import BYTETracker

        self._states = TrackState
        self.config = config
        self._tracker = BYTETracker(SimpleNamespace(**config.model_dump()))
        self.reset()

    def reset(self) -> None:
        self._tracker.reset()
        self._classes = {}
        self._last_index = self._last_timestamp = None

    def update(self, frame: FramePacket, detections: tuple[Detection, ...]) -> tuple[Track, ...]:
        if self._last_index is not None and (
            frame.frame_index != self._last_index + 1 or frame.timestamp_s <= self._last_timestamp
        ):
            raise VisionError(
                "tracking_order", "Tracker requires consecutive indices/increasing PTS"
            )
        tracker = self._tracker
        # Upstream expires after association; enforce the documented hard age before matching.
        tracker.lost_stracks = [
            t
            for t in tracker.lost_stracks
            if t.state == self._states.Lost
            and tracker.frame_id + 1 - t.end_frame <= self.config.track_buffer
        ]
        data = np.asarray(
            [[*d.bbox_xyxy, d.confidence, d.class_id] for d in detections], dtype=np.float64
        ).reshape(-1, 6)
        tracker.update(_Boxes(data))
        live = [
            *tracker.tracked_stracks,
            *[t for t in tracker.lost_stracks if t.state == self._states.Lost],
        ]
        if len(live) > self.config.max_live_tracks:
            raise VisionError("tracking_limit", "Live track limit exceeded; output is incomplete")
        ids = {t.track_id for t in live}
        self._classes = {k: v for k, v in self._classes.items() if k in ids}
        result = []
        for t in live:
            class_id = self._classes.setdefault(t.track_id, int(t.cls))
            if not t.is_activated:
                continue
            observed = t.state == self._states.Tracked
            detection = detections[int(t.idx)] if observed else None
            result.append(
                Track(
                    track_id=int(t.track_id),
                    class_id=class_id,
                    bbox_xyxy=detection.bbox_xyxy if observed else tuple(map(float, t.xyxy)),
                    confidence=detection.confidence if observed else None,
                    state="observed" if observed else "lost",
                )
            )
        self._last_index, self._last_timestamp = frame.frame_index, frame.timestamp_s
        return tuple(result)
