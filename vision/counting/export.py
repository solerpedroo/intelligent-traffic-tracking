"""Streaming event and sparse media-time window exports."""

from collections import Counter
from decimal import Decimal

from vision.pipeline.schemas import CROSSING_EVENTS_COLUMNS, CROSSING_WINDOWS_COLUMNS


class CrossingSink:
    event_fields = CROSSING_EVENTS_COLUMNS
    window_fields = CROSSING_WINDOWS_COLUMNS

    def __init__(self, event_rows, window_rows, window_s, run_id, video_id):
        self.event_rows, self.window_rows = event_rows, window_rows
        self.window_s, self.run_id, self.video_id = window_s, run_id, video_id
        self.bucket = None
        self.counts = Counter()

    def write(self, timestamp_s, events):
        bucket = int(Decimal(str(timestamp_s)) // Decimal(str(self.window_s)))
        if self.bucket is not None and bucket != self.bucket:
            self.flush()
        self.bucket = bucket
        for event in events:
            values = event.model_dump()
            point = values["intersection_xy"]
            values["intersection_xy"] = f"{point[0]},{point[1]}" if point else ""
            self.event_rows.writerow([values[name] for name in self.event_fields])
            self.counts[(event.line_id, event.class_id, event.direction)] += 1

    def flush(self):
        for (line, cls, direction), count in sorted(self.counts.items()):
            self.window_rows.writerow(
                [
                    self.run_id,
                    self.video_id,
                    float(Decimal(self.bucket) * Decimal(str(self.window_s))),
                    float(Decimal(self.bucket + 1) * Decimal(str(self.window_s))),
                    line,
                    cls,
                    direction,
                    count,
                ]
            )
        self.counts.clear()
