import type {
  Catalog,
  HealthResponse,
  JobPage,
  JobRecord,
  JobState,
  ProcessingDefaults,
  TablePage,
  VideoRecord,
} from "@/types/api";

const JOB_STATES = new Set<JobState>([
  "queued",
  "running",
  "completed",
  "failed",
  "cancelled",
]);

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string;

  constructor(status: number, errorCode: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

export function getApiBaseUrl(): string {
  const url = new URL(
    process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
  );
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  ) {
    throw new Error("NEXT_PUBLIC_API_URL must be an HTTP(S) origin");
  }
  return url.origin;
}

export function videoPreviewUrl(videoId: string): string {
  return `${getApiBaseUrl()}/api/videos/${encodeURIComponent(videoId)}/preview`;
}

export function artifactUrl(jobId: string, name: string): string {
  return `${getApiBaseUrl()}/api/jobs/${encodeURIComponent(jobId)}/artifacts/${encodeURIComponent(name)}`;
}

export function heatmapPreviewUrl(jobId: string, name: string): string {
  return `${getApiBaseUrl()}/api/jobs/${encodeURIComponent(jobId)}/heatmaps/${encodeURIComponent(name)}`;
}

export async function fetchArtifactText(
  jobId: string,
  name: string,
  signal?: AbortSignal,
): Promise<string | null> {
  const response = await fetch(artifactUrl(jobId, name), {
    cache: "no-store",
    signal,
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new ApiError(
      response.status,
      "http_error",
      `Request failed (${response.status})`,
    );
  }
  return response.text();
}

async function readBody(response: Response): Promise<unknown> {
  if (!response.ok) {
    let errorCode = "http_error";
    let message = `Request failed (${response.status})`;
    try {
      const data: unknown = await response.json();
      if (isRecord(data) && typeof data.error === "string")
        message = data.error;
      if (isRecord(data) && typeof data.error_code === "string") {
        errorCode = data.error_code;
      }
    } catch {
      // The status line is enough when the body is empty.
    }
    throw new ApiError(response.status, errorCode, message);
  }
  return response.json();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const timeout = AbortSignal.timeout(5_000);
  const response = await fetch(`${getApiBaseUrl()}/api/health`, {
    cache: "no-store",
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
  const data = await readBody(response);
  if (
    !isRecord(data) ||
    data.status !== "ok" ||
    data.service !== "intelligent-traffic-tracking-api" ||
    data.api_version !== "v1"
  ) {
    throw new Error("Unexpected health response");
  }
  return {
    status: "ok",
    service: "intelligent-traffic-tracking-api",
    api_version: "v1",
  };
}

export async function uploadVideo(
  file: File,
  signal?: AbortSignal,
): Promise<VideoRecord> {
  const response = await fetch(`${getApiBaseUrl()}/api/videos`, {
    method: "POST",
    body: file,
    headers: {
      "content-type": "application/octet-stream",
      "x-filename": file.name,
    },
    cache: "no-store",
    signal,
  });
  return parseVideo(await readBody(response));
}

export async function fetchVideo(
  videoId: string,
  signal?: AbortSignal,
): Promise<VideoRecord> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/videos/${encodeURIComponent(videoId)}`,
    {
      cache: "no-store",
      signal,
    },
  );
  return parseVideo(await readBody(response));
}

export async function fetchCatalog(signal?: AbortSignal): Promise<Catalog> {
  const response = await fetch(`${getApiBaseUrl()}/api/models`, {
    cache: "no-store",
    signal,
  });
  const data = await readBody(response);
  if (
    !isRecord(data) ||
    !Array.isArray(data.models) ||
    !Array.isArray(data.tracker_configs)
  ) {
    throw new Error("Unexpected catalog response");
  }
  return {
    models: data.models.filter(isRecord).map((model) => ({
      model_id: String(model.model_id ?? ""),
      classes: Array.isArray(model.classes)
        ? model.classes.filter(isRecord).map((item) => ({
            id: Number(item.id),
            name: String(item.name ?? ""),
          }))
        : [],
    })),
    tracker_configs: data.tracker_configs.filter(isRecord).map((item) => ({
      tracker_config_id: String(item.tracker_config_id ?? ""),
    })),
  };
}

export async function fetchProcessingDefaults(
  signal?: AbortSignal,
): Promise<ProcessingDefaults> {
  const response = await fetch(`${getApiBaseUrl()}/api/processing-defaults`, {
    cache: "no-store",
    signal,
  });
  const data = await readBody(response);
  if (!isRecord(data) || !isRecord(data.detector) || !isRecord(data.tracker)) {
    throw new Error("Unexpected processing defaults");
  }
  const classes = Array.isArray(data.detector.classes)
    ? data.detector.classes.filter(
        (item): item is string => typeof item === "string",
      )
    : [];
  return {
    render_annotated_video: data.render_annotated_video === true,
    start_s: Number(data.start_s ?? 0),
    end_s: data.end_s == null ? null : Number(data.end_s),
    detector: { confidence: Number(data.detector.confidence), classes },
    tracker: {
      track_buffer: Number(data.tracker.track_buffer),
      match_thresh: Number(data.tracker.match_thresh),
      track_low_thresh: Number(data.tracker.track_low_thresh),
    },
  };
}

export async function createJob(
  body: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<JobRecord> {
  const response = await fetch(`${getApiBaseUrl()}/api/jobs`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  return parseJob(await readBody(response));
}

export async function fetchJobs(signal?: AbortSignal): Promise<JobPage> {
  // The jobs API returns this page newest first (created_at descending).
  // Home "Recent jobs" and the jobs board display that page as received.
  // The sort is a safety net if a payload is still oldest-first.
  const response = await fetch(
    `${getApiBaseUrl()}/api/jobs?limit=20&offset=0`,
    {
      cache: "no-store",
      signal,
    },
  );
  const data = await readBody(response);
  if (!isRecord(data) || !Array.isArray(data.items)) {
    throw new Error("Unexpected job list");
  }
  return {
    items: data.items
      .map(parseJob)
      .sort((left, right) => right.created_at.localeCompare(left.created_at)),
    total: Number(data.total ?? 0),
    limit: Number(data.limit ?? 20),
    offset: Number(data.offset ?? 0),
  };
}

export async function fetchJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<JobRecord> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/jobs/${encodeURIComponent(jobId)}`,
    {
      cache: "no-store",
      signal,
    },
  );
  return parseJob(await readBody(response));
}

export async function cancelJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<JobRecord> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/jobs/${encodeURIComponent(jobId)}/cancel`,
    { method: "POST", cache: "no-store", signal },
  );
  return parseJob(await readBody(response));
}

const TABLE_PAGE_SIZE = 100;
const TABLE_ROW_CAP = 1000;

export async function fetchTable(
  jobId: string,
  kind: "events" | "tracks",
  signal?: AbortSignal,
): Promise<TablePage> {
  const items: Record<string, string>[] = [];
  let total = 0;
  let offset = 0;
  while (items.length < TABLE_ROW_CAP) {
    const limit = Math.min(TABLE_PAGE_SIZE, TABLE_ROW_CAP - items.length);
    const page = await fetchTablePage(jobId, kind, limit, offset, signal);
    total = page.total;
    items.push(...page.items);
    offset += page.items.length;
    if (
      page.items.length === 0 ||
      page.items.length < limit ||
      offset >= total
    ) {
      break;
    }
  }
  if (items.length > TABLE_ROW_CAP) items.length = TABLE_ROW_CAP;
  return { items, total, limit: items.length, offset: 0 };
}

async function fetchTablePage(
  jobId: string,
  kind: "events" | "tracks",
  limit: number,
  offset: number,
  signal?: AbortSignal,
): Promise<TablePage> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/jobs/${encodeURIComponent(jobId)}/${kind}?limit=${limit}&offset=${offset}`,
    { cache: "no-store", signal },
  );
  const data = await readBody(response);
  if (!isRecord(data) || !Array.isArray(data.items)) {
    throw new Error("Unexpected table response");
  }
  return {
    items: data.items
      .filter(isRecord)
      .map((row) =>
        Object.fromEntries(
          Object.entries(row).map(([key, value]) => [key, String(value ?? "")]),
        ),
      ),
    total: Number(data.total ?? 0),
    limit: Number(data.limit ?? limit),
    offset: Number(data.offset ?? offset),
  };
}

function parseVideo(data: unknown): VideoRecord {
  if (!isRecord(data) || typeof data.video_id !== "string") {
    throw new Error("Unexpected video response");
  }
  return {
    video_id: data.video_id,
    filename: String(data.filename ?? "video"),
    width: Number(data.width ?? 0),
    height: Number(data.height ?? 0),
    fps: data.fps == null ? null : Number(data.fps),
    duration_s: data.duration_s == null ? null : Number(data.duration_s),
    frame_count: data.frame_count == null ? null : Number(data.frame_count),
    preview_ready: data.preview_ready === true,
    created_at: String(data.created_at ?? ""),
  };
}

function parseJob(data: unknown): JobRecord {
  if (
    !isRecord(data) ||
    typeof data.job_id !== "string" ||
    typeof data.state !== "string"
  ) {
    throw new Error("Unexpected job response");
  }
  if (!JOB_STATES.has(data.state as JobState)) {
    throw new Error("Unexpected job state");
  }
  const config = isRecord(data.config) ? data.config : {};
  return {
    job_id: data.job_id,
    video_id: String(data.video_id ?? ""),
    state: data.state as JobState,
    stage: data.stage == null ? null : String(data.stage),
    processed_frames: Number(data.processed_frames ?? 0),
    total_frames: data.total_frames == null ? null : Number(data.total_frames),
    error_code: data.error_code == null ? null : String(data.error_code),
    error: data.error == null ? null : String(data.error),
    summary_status:
      data.summary_status == null ? null : String(data.summary_status),
    created_at: String(data.created_at ?? ""),
    cancel_requested: data.cancel_requested === true,
    config: {
      render_annotated_video: config.render_annotated_video === true,
      counting: {
        lines:
          isRecord(config.counting) && Array.isArray(config.counting.lines)
            ? config.counting.lines.filter(isRecord).map((line) => ({
                line_id:
                  typeof line.line_id === "string" ? line.line_id : undefined,
              }))
            : [],
      },
    },
  };
}
