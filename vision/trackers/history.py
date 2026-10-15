"""Bounded recent trails and incremental trajectory/lifetime CSV sinks."""

from collections import deque
from dataclasses import dataclass

from vision.pipeline.schemas import LIFETIME_COLUMNS, TRAJECTORY_COLUMNS


@dataclass
class _History:
    class_id: int
    start_s: float
    last_s: float
    observations: int
    points: deque


class TrackHistoryManager:
    trajectory_fields = TRAJECTORY_COLUMNS
    lifetime_fields = LIFETIME_COLUMNS

    def __init__(
        self, run_id, video_id, max_points, trajectory_rows, lifetime_rows, min_observations=3
    ):
        self.run_id, self.video_id = run_id, video_id
        self.max_points = max_points
        self.min_observations = min_observations
        self.trajectory_rows, self.lifetime_rows = trajectory_rows, lifetime_rows
        self.histories = {}
        self.total_tracks = self.total_observations = 0

    def update(self, frame, tracks):
        live_ids = {t.track_id for t in tracks}
        for track_id in self.histories.keys() - live_ids:
            self._close(track_id, "removed")
        for track in tracks:
            if track.state != "observed":
                continue
            if track.track_id not in self.histories:
                self.histories[track.track_id] = _History(
                    track.class_id,
                    frame.timestamp_s,
                    frame.timestamp_s,
                    0,
                    deque(maxlen=self.max_points),
                )
                self.total_tracks += 1
            history = self.histories[track.track_id]
            x1, y1, x2, y2 = track.bbox_xyxy
            point = ((x1 + x2) / 2, y2)
            history.points.append((frame.frame_index, frame.timestamp_s, *point))
            history.last_s = frame.timestamp_s
            history.observations += 1
            self.total_observations += 1
            self.trajectory_rows.writerow(
                [
                    self.run_id,
                    self.video_id,
                    frame.frame_index,
                    frame.timestamp_s,
                    track.track_id,
                    track.class_id,
                    track.confidence,
                    *track.bbox_xyxy,
                    *point,
                ]
            )

    def _close(self, track_id, reason):
        history = self.histories.pop(track_id)
        self.lifetime_rows.writerow(
            [
                self.run_id,
                self.video_id,
                track_id,
                history.class_id,
                history.start_s,
                history.last_s,
                history.last_s - history.start_s,
                history.observations,
                reason,
                history.observations >= self.min_observations,
            ]
        )

    def finish(self):
        for track_id in list(self.histories):
            self._close(track_id, "selection_end_censored")
