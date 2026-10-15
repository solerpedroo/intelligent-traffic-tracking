"""Bounded per-class/window observation histograms; no frame/time weighting."""

from collections import Counter
from decimal import Decimal

import numpy as np

from vision.contracts.errors import VisionError
from vision.geometry import bottom_center


def resolve_heatmap_classes(config, class_ids):
    selected = tuple(config.class_ids or class_ids)
    if (
        not selected
        or len(selected) > 16
        or len(set(selected)) != len(selected)
        or not set(selected) <= set(class_ids)
    ):
        raise VisionError("heatmap_classes", "Select 1–16 unique detector class IDs for heatmaps")
    return selected


class HeatmapAccumulator:
    def __init__(self, config, width, height, class_ids, emit, max_live_tracks=4000):
        self.config, self.width, self.height = config, width, height
        self.class_ids = resolve_heatmap_classes(config, class_ids)
        self.max_live_tracks = max_live_tracks
        self.emit = emit
        self.reset()

    def reset(self):
        self.bucket = None
        self.grids = {}
        self.total_observations = Counter()
        self.windows = 0
        self._last_index = self._last_s = None
        self._finished = False

    def update(self, frame, tracks):
        if self._finished or (
            self._last_index is not None
            and (frame.frame_index != self._last_index + 1 or frame.timestamp_s <= self._last_s)
        ):
            raise VisionError("heatmap_order", "Heatmaps require consecutive frames/increasing PTS")
        ids = {track.track_id for track in tracks}
        if len(ids) != len(tracks) or len(ids) > self.max_live_tracks:
            raise VisionError("heatmap_limit", "Duplicate IDs or live track limit exceeded")
        bucket = int(Decimal(str(frame.timestamp_s)) // Decimal(str(self.config.window_s)))
        if bucket != self.bucket:
            self._flush_window()
            self.bucket = bucket
            self.grids = {
                class_id: np.zeros(
                    (self.config.grid_height, self.config.grid_width), dtype=np.uint64
                )
                for class_id in self.class_ids
            }
        for track in tracks:
            if track.state != "observed" or track.class_id not in self.grids:
                continue
            x, y = bottom_center(track.bbox_xyxy)
            if 0 <= x <= self.width and 0 <= y <= self.height:
                column = min(
                    self.config.grid_width - 1, int(x / self.width * self.config.grid_width)
                )
                row = min(
                    self.config.grid_height - 1, int(y / self.height * self.config.grid_height)
                )
                self.grids[track.class_id][row, column] += 1
                self.total_observations[track.class_id] += 1
        self._last_index, self._last_s = frame.frame_index, frame.timestamp_s

    def _flush_window(self):
        if self.bucket is not None:
            # Sink consumes borrowed grids synchronously, before a new window is allocated.
            self.emit(self.bucket, self.grids)
            self.windows += 1
            self.bucket = None
            self.grids = {}

    def finish(self):
        if not self._finished:
            self._flush_window()
            self._finished = True

    def summary(self):
        return {
            "unit": "observations_per_grid_cell",
            "weighting": "one_per_observed_track_per_frame",
            "windows_with_processed_frames": self.windows,
            "class_observations": {str(k): self.total_observations[k] for k in self.class_ids},
            "config": self.config.model_dump(mode="json"),
        }
