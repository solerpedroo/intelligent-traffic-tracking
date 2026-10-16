const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;

export type UnitPoint = { x: number; y: number };

export type LineDraft = {
  lineId: string;
  start: UnitPoint;
  end: UnitPoint;
};

export type ZoneVertex = UnitPoint & { id: string };

export type ZoneDraft = {
  zoneId: string;
  vertices: ZoneVertex[];
};

export type JobDraft = {
  detectorModelId: string;
  trackerConfigId: string;
  renderAnnotatedVideo: boolean;
  startS: string;
  endS: string;
  classes: string[];
  confidence: string;
  trackBuffer: string;
  matchThresh: string;
  lines: LineDraft[];
  zones: ZoneDraft[];
};

export function blankLine(index: number): LineDraft {
  return {
    lineId: `line-${index + 1}`,
    start: { x: 0.2, y: 0.5 },
    end: { x: 0.8, y: 0.5 },
  };
}

let vertexSerial = 0;

export function zoneVertex(x: number, y: number): ZoneVertex {
  vertexSerial += 1;
  return { id: `vertex-${vertexSerial}`, x, y };
}

export function blankZone(index: number): ZoneDraft {
  return {
    zoneId: `zone-${index + 1}`,
    vertices: [
      zoneVertex(0.2, 0.2),
      zoneVertex(0.5, 0.2),
      zoneVertex(0.5, 0.5),
    ],
  };
}

function inUnit(value: number): boolean {
  return Number.isFinite(value) && value >= 0 && value <= 1;
}

export function validateDraft(draft: JobDraft): string | null {
  const start = Number(draft.startS);
  if (!Number.isFinite(start) || start < 0) {
    return "Start time must be zero or greater.";
  }
  if (draft.endS.trim() !== "") {
    const end = Number(draft.endS);
    if (!Number.isFinite(end) || end <= start) {
      return "End time must be greater than the start time.";
    }
  }
  const confidence = Number(draft.confidence);
  if (!Number.isFinite(confidence) || confidence < 0 || confidence > 1) {
    return "Detection confidence must be between 0 and 1.";
  }
  const trackBuffer = Number(draft.trackBuffer);
  if (!Number.isInteger(trackBuffer) || trackBuffer < 1 || trackBuffer > 300) {
    return "Track buffer must be an integer from 1 to 300.";
  }
  const matchThresh = Number(draft.matchThresh);
  if (!Number.isFinite(matchThresh) || matchThresh <= 0 || matchThresh > 1) {
    return "Match threshold must be greater than 0 and at most 1.";
  }
  if (draft.classes.length === 0) {
    return "Select at least one class.";
  }
  const lineIds = new Set<string>();
  for (const line of draft.lines) {
    if (!IDENTIFIER.test(line.lineId)) {
      return "Each line ID must start with a letter or digit.";
    }
    if (lineIds.has(line.lineId)) return "Line IDs must be unique.";
    lineIds.add(line.lineId);
    const points = [line.start, line.end];
    if (points.some((point) => !inUnit(point.x) || !inUnit(point.y))) {
      return "Line coordinates must stay between 0 and 1.";
    }
    if (line.start.x === line.end.x && line.start.y === line.end.y) {
      return "Line endpoints must be distinct.";
    }
  }
  const zoneIds = new Set<string>();
  for (const zone of draft.zones) {
    if (!IDENTIFIER.test(zone.zoneId)) {
      return "Each zone ID must start with a letter or digit.";
    }
    if (zoneIds.has(zone.zoneId)) return "Zone IDs must be unique.";
    zoneIds.add(zone.zoneId);
    if (zone.vertices.length < 3)
      return "A zone needs at least three vertices.";
    if (zone.vertices.some((point) => !inUnit(point.x) || !inUnit(point.y))) {
      return "Zone coordinates must stay between 0 and 1.";
    }
  }
  const needsTracker = draft.lines.length > 0 || draft.zones.length > 0;
  if (needsTracker && (!draft.detectorModelId || !draft.trackerConfigId)) {
    return "Lines and zones require a detector and a tracker.";
  }
  return null;
}

export function toJobBody(
  videoId: string,
  draft: JobDraft,
): Record<string, unknown> {
  return {
    video_id: videoId,
    detector_model_id: draft.detectorModelId || null,
    tracker_config_id: draft.trackerConfigId || null,
    render_annotated_video: draft.renderAnnotatedVideo,
    start_s: Number(draft.startS),
    end_s: draft.endS.trim() === "" ? null : Number(draft.endS),
    detector: {
      classes: draft.classes,
      confidence: Number(draft.confidence),
    },
    tracker: {
      track_buffer: Number(draft.trackBuffer),
      match_thresh: Number(draft.matchThresh),
    },
    counting: {
      lines: draft.lines.map((line) => ({
        line_id: line.lineId,
        start: [line.start.x, line.start.y],
        end: [line.end.x, line.end.y],
      })),
    },
    analytics: {
      zones: draft.zones.map((zone) => ({
        zone_id: zone.zoneId,
        vertices: zone.vertices.map((point) => [point.x, point.y]),
      })),
    },
  };
}
