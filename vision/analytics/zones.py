"""ROI observations and visits; unknown intervals never become observed dwell."""

from collections import Counter
from dataclasses import dataclass, field
from types import SimpleNamespace

from vision.contracts import ZoneEvent, ZoneVisit
from vision.contracts.errors import VisionError
from vision.geometry import bottom_center
from vision.geometry.polygons import contains


@dataclass
class _Visit:
    visit_id: int
    first_frame: int
    last_frame: int
    first_s: float
    last_s: float
    left_censored: bool
    start_reason: str
    observations: int = 1
    dwell_s: float = 0.0


@dataclass
class _Track:
    class_id: int
    last_frame: int | None = None
    last_s: float | None = None
    observed_before: bool = False
    visits: dict[str, _Visit] = field(default_factory=dict)


@dataclass(frozen=True)
class ZoneBatch:
    events: tuple[ZoneEvent, ...]
    occupancy: tuple[tuple, ...]


class ZoneAnalytics:
    occupancy_fields = (
        "run_id",
        "video_id",
        "frame_index",
        "timestamp_s",
        "zone_id",
        "class_id",
        "observed_count",
    )

    def __init__(
        self, config, width, height, class_ids, run_id, video_id, emit_visit, max_live_tracks=4000
    ):
        self.config, self.width, self.height = config, width, height
        self.class_ids = tuple(class_ids)
        self.emit_visit = emit_visit
        self.max_live_tracks = max_live_tracks
        self.reset(run_id, video_id)

    def reset(self, run_id, video_id):
        self.run_id, self.video_id = run_id, video_id
        self.states = {}
        self.metrics = {}
        self.max_occupancy = Counter()
        self.current_occupancy = Counter()
        self.total_visits = 0
        self._last = None
        self._finished = False

    def _metric(self, zone_id, class_id):
        return self.metrics.setdefault((zone_id, class_id), Counter())

    def _event(self, frame, track_id, class_id, zone_id, visit_id, kind, reason):
        return ZoneEvent(
            run_id=self.run_id,
            video_id=self.video_id,
            track_id=track_id,
            class_id=class_id,
            zone_id=zone_id,
            visit_id=visit_id,
            event_type=kind,
            reason=reason,
            frame_index=frame.frame_index,
            timestamp_s=frame.timestamp_s,
        )

    def _close(self, frame, track_id, state, zone_id, reason, kind):
        visit = state.visits.pop(zone_id)
        self.emit_visit(
            ZoneVisit(
                run_id=self.run_id,
                video_id=self.video_id,
                visit_id=visit.visit_id,
                track_id=track_id,
                class_id=state.class_id,
                zone_id=zone_id,
                first_inside_frame=visit.first_frame,
                last_inside_frame=visit.last_frame,
                first_inside_s=visit.first_s,
                last_inside_s=visit.last_s,
                observed_dwell_s=visit.dwell_s,
                observations=visit.observations,
                left_censored=visit.left_censored,
                right_censored=reason != "zone_exit",
                start_reason=visit.start_reason,
                end_reason=reason,
                closed_frame=frame.frame_index,
                closed_s=frame.timestamp_s,
            )
        )
        metric = self._metric(zone_id, state.class_id)
        metric[reason] += 1
        metric["closed_visits"] += 1
        return self._event(frame, track_id, state.class_id, zone_id, visit.visit_id, kind, reason)

    def _lose(self, frame, track_id, state, reason):
        events = []
        for zone_id in tuple(state.visits):
            event = self._close(
                frame, track_id, state, zone_id, "observation_lost", "observation_lost"
            )
            events.append(event.model_copy(update={"reason": reason}))
        state.last_frame = state.last_s = None
        return events

    def update(self, frame, tracks):
        if self._finished or (
            self._last is not None
            and (
                frame.frame_index != self._last.frame_index + 1
                or frame.timestamp_s <= self._last.timestamp_s
            )
        ):
            raise VisionError(
                "analytics_order",
                "Analytics requires consecutive frames/increasing PTS; reset after finish",
            )
        ids = {track.track_id for track in tracks}
        if len(ids) != len(tracks) or len(ids) > self.max_live_tracks:
            raise VisionError("analytics_limit", "Duplicate IDs or live track limit exceeded")
        events = []
        for track_id in self.states.keys() - ids:
            events.extend(self._lose(frame, track_id, self.states.pop(track_id), "track_removed"))
        occupancy = Counter()
        for track in tracks:
            state = self.states.get(track.track_id)
            if state is not None and state.class_id != track.class_id:
                raise VisionError("analytics_class", "Track class must stay stable")
            if track.state != "observed":
                if state is not None:
                    events.extend(self._lose(frame, track.track_id, state, "missing_observation"))
                continue
            if track.class_id not in self.class_ids:
                raise VisionError("analytics_class", "Class not selected for analytics")
            state = self.states.setdefault(track.track_id, _Track(track.class_id))
            x, y = bottom_center(track.bbox_xyxy)
            if not (0 <= x <= self.width and 0 <= y <= self.height):
                events.extend(self._lose(frame, track.track_id, state, "out_of_image"))
                continue
            if state.last_frame is not None and (
                frame.frame_index != state.last_frame + 1
                or frame.timestamp_s - state.last_s > self.config.max_gap_s + 1e-9
            ):
                events.extend(self._lose(frame, track.track_id, state, "timestamp_gap"))
            for zone in self.config.zones:
                metric = self._metric(zone.zone_id, track.class_id)
                if contains(zone.vertices, (x / self.width, y / self.height)):
                    occupancy[(zone.zone_id, track.class_id)] += 1
                    metric["presence_observations"] += 1
                    visit = state.visits.get(zone.zone_id)
                    if visit is None:
                        censored = state.last_frame is None
                        reason = (
                            "transition"
                            if not censored
                            else (
                                "after_observation_loss"
                                if state.observed_before
                                else (
                                    "selection_start"
                                    if self._last is None
                                    else "first_observation_inside"
                                )
                            )
                        )
                        self.total_visits += 1
                        visit = _Visit(
                            self.total_visits,
                            frame.frame_index,
                            frame.frame_index,
                            frame.timestamp_s,
                            frame.timestamp_s,
                            censored,
                            reason,
                        )
                        state.visits[zone.zone_id] = visit
                        metric["visits"] += 1
                        metric["censored_starts" if censored else "zone_enter"] += 1
                        events.append(
                            self._event(
                                frame,
                                track.track_id,
                                track.class_id,
                                zone.zone_id,
                                visit.visit_id,
                                "boundary_censored" if censored else "zone_enter",
                                reason,
                            )
                        )
                    else:
                        dt = frame.timestamp_s - visit.last_s
                        visit.dwell_s += dt
                        visit.observations += 1
                        visit.last_frame, visit.last_s = frame.frame_index, frame.timestamp_s
                        metric["observed_dwell_s"] += dt
                elif zone.zone_id in state.visits:
                    events.append(
                        self._close(
                            frame, track.track_id, state, zone.zone_id, "zone_exit", "zone_exit"
                        )
                    )
            state.last_frame, state.last_s = frame.frame_index, frame.timestamp_s
            state.observed_before = True
        self.current_occupancy = occupancy
        for zone in self.config.zones:
            total = sum(
                count for (zone_id, _), count in occupancy.items() if zone_id == zone.zone_id
            )
            self.max_occupancy[zone.zone_id] = max(self.max_occupancy[zone.zone_id], total)
        self._last = SimpleNamespace(frame_index=frame.frame_index, timestamp_s=frame.timestamp_s)
        rows = tuple(
            (
                self.run_id,
                self.video_id,
                frame.frame_index,
                frame.timestamp_s,
                zone.zone_id,
                class_id,
                occupancy[(zone.zone_id, class_id)],
            )
            for zone in self.config.zones
            for class_id in self.class_ids
        )
        return ZoneBatch(tuple(events), rows)

    def finish(self):
        if self._finished:
            return ()
        events = []
        for track_id, state in self.states.items():
            for zone_id in tuple(state.visits):
                events.append(
                    self._close(
                        self._last, track_id, state, zone_id, "selection_end", "boundary_censored"
                    )
                )
        self.states.clear()
        self._finished = True
        return tuple(events)

    def summary(self):
        return {
            "total_visits": self.total_visits,
            "dwell_unit": "seconds_between_consecutive_inside_observations",
            "by_zone_class": [
                {
                    "zone_id": zone.zone_id,
                    "class_id": class_id,
                    **{
                        key: self.metrics.get((zone.zone_id, class_id), {}).get(key, 0)
                        for key in (
                            "visits",
                            "zone_enter",
                            "zone_exit",
                            "censored_starts",
                            "observation_lost",
                            "selection_end",
                            "closed_visits",
                            "presence_observations",
                            "observed_dwell_s",
                        )
                    },
                }
                for zone in self.config.zones
                for class_id in self.class_ids
            ],
            "max_observed_occupancy": dict(self.max_occupancy),
        }
