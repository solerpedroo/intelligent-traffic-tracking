"""Finite path evidence, stable sides and once-per-ID/direction counting."""

from collections import Counter
from dataclasses import dataclass, field

from vision.contracts import CrossingEvent
from vision.contracts.errors import VisionError
from vision.geometry import PixelLine, bottom_center


@dataclass
class _LineState:
    last_sign: int = 0
    side: int = 0
    candidate: int = 0
    streak: int = 0
    anchor_frame: int = 0
    anchor_s: float = 0.0
    intersection: tuple[float, float] | None = None
    emitted: set[str] = field(default_factory=set)

    def break_evidence(self):
        self.last_sign = self.side = self.candidate = self.streak = 0
        self.intersection = None


@dataclass
class _TrackState:
    class_id: int
    observations: int = 0
    previous: tuple[float, float] | None = None
    frame_index: int = 0
    timestamp_s: float = 0.0
    lines: dict[str, _LineState] = field(default_factory=dict)


class LineCounter:
    """IDs must be unique within a run, as guaranteed by the ByteTrack adapter.

    Only live/lost IDs retain evidence and direction flags. Geometry is invalidated
    at a large gap or an out-of-image observation; emitted flags survive that gap.
    The event time is the confirmation frame, not an interpolated crossing time.
    """

    def __init__(self, config, width, height, run_id, video_id, max_live_tracks=4000):
        self.config, self.width, self.height = config, width, height
        self.lines = tuple(PixelLine.from_config(line, width, height) for line in config.lines)
        self.max_live_tracks = max_live_tracks
        self.reset(run_id, video_id)

    def reset(self, run_id, video_id):
        self.run_id, self.video_id = run_id, video_id
        self.states = {}
        self.counts = Counter()
        self._last_index = self._last_s = None

    def update(self, frame, tracks):
        if self._last_index is not None and (
            frame.frame_index != self._last_index + 1 or frame.timestamp_s <= self._last_s
        ):
            raise VisionError(
                "counting_order", "Counter requires consecutive frames/increasing PTS"
            )
        ids = {t.track_id for t in tracks}
        if len(ids) != len(tracks) or len(ids) > self.max_live_tracks:
            raise VisionError("counting_limit", "Duplicate IDs or live track limit exceeded")
        self.states = {key: value for key, value in self.states.items() if key in ids}
        events = []
        for track in tracks:
            if track.state != "observed":
                continue
            state = self.states.setdefault(track.track_id, _TrackState(track.class_id))
            if state.class_id != track.class_id:
                raise VisionError("counting_class", "Track class must remain stable within a run")
            point = bottom_center(track.bbox_xyxy)
            valid = 0 <= point[0] <= self.width and 0 <= point[1] <= self.height
            gap = state.previous is not None and (
                frame.frame_index - state.frame_index > self.config.max_gap_frames
                or frame.timestamp_s - state.timestamp_s > self.config.max_gap_s + 1e-9
            )
            if gap or not valid:
                for line_state in state.lines.values():
                    line_state.break_evidence()
                state.previous = None
            if not valid:
                continue
            state.observations += 1
            for line in self.lines:
                line_state = state.lines.setdefault(line.line_id, _LineState())
                event = self._advance(frame, track, state, line, line_state, point)
                if event is not None:
                    events.append(event)
                    self.counts[(line.line_id, track.class_id, event.direction)] += 1
            state.previous, state.frame_index, state.timestamp_s = (
                point,
                frame.frame_index,
                frame.timestamp_s,
            )
        self._last_index, self._last_s = frame.frame_index, frame.timestamp_s
        return tuple(events)

    def _advance(self, frame, track, state, line, ls, point):
        distance = line.signed_distance(point)
        side = (
            -1
            if distance < -self.config.hysteresis_px
            else (1 if distance > self.config.hysteresis_px else 0)
        )
        sign = -1 if distance < -1e-9 else (1 if distance > 1e-9 else 0)
        if ls.side and sign and ls.last_sign and sign != ls.last_sign:
            ls.intersection = line.intersection(state.previous, point) if sign != ls.side else None
        if sign:
            ls.last_sign = sign
        if side == 0:
            ls.candidate = ls.streak = 0
            return None
        if side == ls.candidate:
            ls.streak += 1
        else:
            ls.candidate, ls.streak = side, 1
        if side == ls.side:
            ls.anchor_frame, ls.anchor_s = frame.frame_index, frame.timestamp_s
            ls.intersection = None
            return None
        if ls.streak < self.config.stable_observations:
            return None
        event = None
        if (
            ls.side
            and ls.intersection is not None
            and state.observations >= self.config.min_observations
        ):
            direction = "A_TO_B" if ls.side < side else "B_TO_A"
            if direction not in ls.emitted:
                ls.emitted.add(direction)
                event = CrossingEvent(
                    run_id=self.run_id,
                    video_id=self.video_id,
                    frame_index=frame.frame_index,
                    timestamp_s=frame.timestamp_s,
                    track_id=track.track_id,
                    class_id=track.class_id,
                    line_id=line.line_id,
                    direction=direction,
                    evidence_start_frame=ls.anchor_frame,
                    evidence_start_s=ls.anchor_s,
                    intersection_xy=ls.intersection,
                    observed_count=state.observations,
                )
        ls.side = side
        ls.anchor_frame, ls.anchor_s = frame.frame_index, frame.timestamp_s
        ls.intersection = None
        return event

    def summary(self):
        return {
            "total_events": sum(self.counts.values()),
            "by_line_class_direction": [
                {"line_id": line, "class_id": cls, "direction": direction, "count": count}
                for (line, cls, direction), count in sorted(self.counts.items())
            ],
            "by_line_direction": [
                {
                    "line_id": line.line_id,
                    "direction": direction,
                    "count": sum(
                        n
                        for (lid, _, d), n in self.counts.items()
                        if lid == line.line_id and d == direction
                    ),
                }
                for line in self.lines
                for direction in ("A_TO_B", "B_TO_A")
            ],
        }
