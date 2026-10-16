import { parseCsv } from "@/lib/csv";

export type Metric = {
  status: "measured" | "not_evaluated";
  reason: string | null;
};

export type CountBar = {
  key: string;
  label: string;
  count: number;
  unit: "events";
};

export type SeriesPoint = {
  key: string;
  startS: number;
  endS: number;
  count: number;
};

export type OccupancyBar = {
  key: string;
  label: string;
  maximum: number;
  mean: number;
  frames: number;
};

export type TrackSpan = {
  trackId: string;
  classLabel: string;
  spanS: number;
  observations: number;
  eligible: boolean;
  closure: string;
};

export type HeatmapCard = {
  key: string;
  classLabel: string;
  windowStartS: number;
  windowEndS: number;
  observations: number;
  unit: string;
  previewName: string | null;
};

export type AnalyticsReport = {
  counts: Metric & { total: number | null; bars: CountBar[] };
  series: Metric & { points: SeriesPoint[]; windowNote: string };
  occupancy: Metric & { bars: OccupancyBar[] };
  tracks: Metric & { spans: TrackSpan[] };
  heatmaps: Metric & { cards: HeatmapCard[] };
  performance: {
    elapsedS: Metric & { value: number | null };
    endToEndFps: Metric & { value: number | null };
    inferenceFps: Metric & { value: number | null };
    meanInferenceMs: Metric & { value: number | null };
  };
  fragmentation: Metric & { suspectedLosses: TrackSpan[] };
};

export type RunFacts = {
  jobId: string;
  videoId: string;
  startS: number;
  endS: number | null;
  modelId: string | null;
  checkpoint: string | null;
  trackerId: string | null;
  trackerSignature: string;
  geometry: string;
  device: string | null;
  hardware: string | null;
};

export type Comparison = {
  controlled: boolean;
  differences: string[];
  statement: string;
};

type ClassName = { id: number; name: string };

export function buildAnalytics(input: {
  summary: unknown;
  windowsText: string | null;
  lifetimesText: string | null;
  occupancyText: string | null;
  heatmapText: string | null;
  classes: ClassName[];
}): AnalyticsReport {
  const summary = asRecord(input.summary);
  const names = new Map(input.classes.map((item) => [item.id, item.name]));
  const label = (classId: string) =>
    names.get(Number(classId)) ?? `class ${classId}`;
  return {
    counts: countsFrom(summary),
    series: seriesFrom(input.windowsText),
    occupancy: occupancyFrom(input.occupancyText, label),
    tracks: tracksFrom(input.lifetimesText, label),
    heatmaps: heatmapsFrom(input.heatmapText, label),
    performance: performanceFrom(summary),
    fragmentation: fragmentationFrom(summary, input.lifetimesText, label),
  };
}

export function runFacts(
  jobId: string,
  config: unknown,
  manifest: unknown,
): RunFacts {
  const resolved = asRecord(config);
  const manifestRecord = asRecord(manifest);
  const detector = asRecord(resolved?.detector);
  const tracker = asRecord(resolved?.tracker);
  const counting = asRecord(resolved?.counting);
  const analytics = asRecord(resolved?.analytics);
  const reference = asRecord(manifestRecord?.detector);
  return {
    jobId,
    videoId: stringOr(
      resolved?.video_id,
      stringOr(manifestRecord?.video_id, ""),
    ),
    startS: numberOr(resolved?.start_s, 0),
    endS: resolved?.end_s == null ? null : numberOr(resolved.end_s, 0),
    modelId:
      resolved?.detector_model_id == null
        ? null
        : String(resolved.detector_model_id),
    checkpoint:
      reference?.checkpoint_sha256 == null
        ? null
        : String(reference.checkpoint_sha256),
    trackerId:
      resolved?.tracker_config_id == null
        ? null
        : String(resolved.tracker_config_id),
    trackerSignature: stable({
      track_buffer: tracker?.track_buffer,
      match_thresh: tracker?.match_thresh,
      track_low_thresh: tracker?.track_low_thresh,
      track_high_thresh: tracker?.track_high_thresh,
    }),
    geometry: stable({
      lines: counting?.lines ?? [],
      zones: analytics?.zones ?? [],
    }),
    device: detector?.device == null ? null : String(detector.device),
    hardware:
      manifestRecord?.hardware == null ? null : String(manifestRecord.hardware),
  };
}

export function compareRuns(left: RunFacts, right: RunFacts): Comparison {
  const differences: string[] = [];
  if (left.videoId !== right.videoId) differences.push("Different videos");
  if (left.startS !== right.startS || left.endS !== right.endS) {
    differences.push("Different time ranges");
  }
  if (left.geometry !== right.geometry)
    differences.push("Different lines or zones");
  if (left.modelId !== right.modelId || left.checkpoint !== right.checkpoint) {
    differences.push("Different detector weights");
  }
  if (
    left.trackerId !== right.trackerId ||
    left.trackerSignature !== right.trackerSignature
  ) {
    differences.push("Different tracker settings");
  }
  if (left.device !== right.device || left.hardware !== right.hardware) {
    differences.push("Different hardware or device");
  }
  const controlled = differences.length === 0;
  return {
    controlled,
    differences,
    statement: controlled
      ? "These runs share video, interval, geometry, weights, tracker settings, and hardware. This view does not claim statistical significance."
      : "These runs are not a controlled ablation. The differences below mean the counts are separate observations, not a causal comparison.",
  };
}

export function reconcileWindows(
  summary: unknown,
  windowsText: string,
): { ok: boolean; mismatches: string[] } {
  const counting = asRecord(asRecord(summary)?.counting);
  const expected = new Map<string, number>();
  for (const row of asRecords(counting?.by_line_class_direction)) {
    const key = `${row.line_id}|${row.class_id}|${row.direction}`;
    expected.set(key, numberOr(row.count, 0));
  }
  const actual = new Map<string, number>();
  for (const row of parseCsv(windowsText)) {
    const key = `${row.line_id}|${row.class_id}|${row.direction}`;
    actual.set(key, (actual.get(key) ?? 0) + numberOr(row.count, 0));
  }
  const mismatches: string[] = [];
  for (const [key, count] of expected) {
    if ((actual.get(key) ?? 0) !== count) mismatches.push(key);
  }
  for (const key of actual.keys()) {
    if (!expected.has(key)) mismatches.push(key);
  }
  return { ok: mismatches.length === 0, mismatches };
}

function countsFrom(
  summary: Record<string, unknown> | null,
): AnalyticsReport["counts"] {
  const counting = asRecord(summary?.counting);
  if (!counting) {
    return {
      status: "not_evaluated",
      reason: "This job has no counting summary. A missing count is not zero.",
      total: null,
      bars: [],
    };
  }
  const bars = asRecords(counting.by_line_direction).map((row) => ({
    key: `${row.line_id}-${row.direction}`,
    label: `${row.line_id} ${row.direction}`,
    count: numberOr(row.count, 0),
    unit: "events" as const,
  }));
  return {
    status: "measured",
    reason: null,
    total: numberOr(counting.total_events, 0),
    bars,
  };
}

function seriesFrom(text: string | null): AnalyticsReport["series"] {
  if (text == null) {
    return {
      status: "not_evaluated",
      reason: "crossing_windows.csv is not in this job.",
      points: [],
      windowNote:
        "Sparse windows omit empty intervals. A gap is not a measured zero.",
    };
  }
  const grouped = new Map<string, SeriesPoint>();
  for (const row of parseCsv(text)) {
    const startS = Number(row.window_start_s);
    const endS = Number(row.window_end_s);
    if (!Number.isFinite(startS) || !Number.isFinite(endS)) continue;
    const key = `${startS}-${endS}`;
    const current = grouped.get(key) ?? { key, startS, endS, count: 0 };
    current.count += numberOr(row.count, 0);
    grouped.set(key, current);
  }
  return {
    status: "measured",
    reason: grouped.size === 0 ? "The export has no crossing windows." : null,
    points: [...grouped.values()],
    windowNote:
      "Each bar sums exported rows in that media-time window. Empty windows are absent from the sparse CSV and are not drawn as zero.",
  };
}

function occupancyFrom(
  text: string | null,
  label: (classId: string) => string,
): AnalyticsReport["occupancy"] {
  if (text == null) {
    return {
      status: "not_evaluated",
      reason: "zone_occupancy.csv is not in this job. Occupancy is not zero.",
      bars: [],
    };
  }
  const groups = new Map<string, { label: string; values: number[] }>();
  for (const row of parseCsv(text)) {
    const key = `${row.zone_id}|${row.class_id}`;
    const current = groups.get(key) ?? {
      label: `${row.zone_id} · ${label(row.class_id ?? "")}`,
      values: [],
    };
    current.values.push(numberOr(row.observed_count, 0));
    groups.set(key, current);
  }
  return {
    status: "measured",
    reason: groups.size === 0 ? "The occupancy export has no rows." : null,
    bars: [...groups.entries()].map(([key, group]) => ({
      key,
      label: group.label,
      maximum: Math.max(...group.values),
      mean:
        group.values.reduce((sum, value) => sum + value, 0) /
        group.values.length,
      frames: group.values.length,
    })),
  };
}

function tracksFrom(
  text: string | null,
  label: (classId: string) => string,
): AnalyticsReport["tracks"] {
  if (text == null) {
    return {
      status: "not_evaluated",
      reason: "track-lifetimes.csv is not in this job.",
      spans: [],
    };
  }
  const spans = parseCsv(text).map((row) => ({
    trackId: row.track_id ?? "",
    classLabel: label(row.class_id ?? ""),
    spanS: numberOr(row.observed_span_s, 0),
    observations: numberOr(row.observations, 0),
    eligible:
      row.analysis_eligible === "True" || row.analysis_eligible === "true",
    closure: row.closure_reason ?? "",
  }));
  return {
    status: "measured",
    reason: spans.length === 0 ? "No track lifetimes were exported." : null,
    spans,
  };
}

function heatmapsFrom(
  text: string | null,
  label: (classId: string) => string,
): AnalyticsReport["heatmaps"] {
  if (text == null) {
    return {
      status: "not_evaluated",
      reason: "heatmap_index.csv is not in this job. Heat was not measured.",
      cards: [],
    };
  }
  const cards = parseCsv(text).map((row) => {
    const preview = row.preview_file?.split("/").pop() ?? "";
    return {
      key: `${row.window_start_s}-${row.class_id}-${preview}`,
      classLabel: label(row.class_id ?? ""),
      windowStartS: numberOr(row.window_start_s, 0),
      windowEndS: numberOr(row.window_end_s, 0),
      observations: numberOr(row.observations, 0),
      unit: row.unit || "observations_per_grid_cell",
      previewName: /^[A-Za-z0-9][A-Za-z0-9_.-]*\.png$/.test(preview)
        ? preview
        : null,
    };
  });
  return {
    status: "measured",
    reason: cards.length === 0 ? "The heatmap index has no windows." : null,
    cards,
  };
}

function performanceFrom(
  summary: Record<string, unknown> | null,
): AnalyticsReport["performance"] {
  const detector = asRecord(summary?.detector);
  const elapsed = finite(summary?.elapsed_s);
  const endToEnd = finite(summary?.end_to_end_fps);
  const inference = finite(summary?.inference_fps);
  const mean = finite(detector?.mean_inference_ms);
  return {
    elapsedS: metric(elapsed, "s", "elapsed_s is missing from summary.json"),
    endToEndFps: metric(
      endToEnd,
      "frames/s",
      "end_to_end_fps is missing. It includes load and warmup, and is not detector FPS.",
    ),
    inferenceFps: metric(
      inference,
      "forwards/s",
      "inference_fps is not evaluated. No detector time was recorded, and this is not zero.",
    ),
    meanInferenceMs: metric(
      mean,
      "ms",
      "mean inference time is not evaluated without a detector summary.",
    ),
  };
}

function fragmentationFrom(
  summary: Record<string, unknown> | null,
  lifetimesText: string | null,
  label: (classId: string) => string,
): AnalyticsReport["fragmentation"] {
  const suspected =
    lifetimesText == null
      ? []
      : tracksFrom(lifetimesText, label).spans.filter(
          (span) => span.closure === "observation_lost",
        );
  const switches = asRecord(summary?.tracker)?.id_switches;
  if (typeof switches === "number" && Number.isFinite(switches)) {
    return {
      status: "measured",
      reason: `Confirmed ID switches from ground truth: ${switches}.`,
      suspectedLosses: suspected,
    };
  }
  return {
    status: "not_evaluated",
    reason:
      "Confirmed ID switches need ground truth. observation_lost closures are suspected losses, not identity switches, and they are not a fragmentation score.",
    suspectedLosses: suspected,
  };
}

function metric(
  value: number | null,
  _unit: string,
  reason: string,
): Metric & { value: number | null } {
  if (value == null) return { status: "not_evaluated", reason, value: null };
  return { status: "measured", reason: null, value };
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asRecords(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value)
    ? value.filter(
        (item): item is Record<string, unknown> => asRecord(item) !== null,
      )
    : [];
}

function stringOr(value: unknown, fallback: string): string {
  return typeof value === "string" && value !== "" ? value : fallback;
}

function numberOr(value: unknown, fallback: number): number {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stable(value: unknown): string {
  return JSON.stringify(sortValue(value));
}

function sortValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortValue);
  if (asRecord(value)) {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, sortValue(item)]),
    );
  }
  return value;
}
