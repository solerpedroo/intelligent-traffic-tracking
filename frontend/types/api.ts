/** Liveness only: does not imply detector, data, or worker readiness. */
export type HealthResponse = {
  status: "ok";
  service: "intelligent-traffic-tracking-api";
  api_version: "v1";
};

export type VideoRecord = {
  video_id: string;
  filename: string;
  width: number;
  height: number;
  fps: number | null;
  duration_s: number | null;
  frame_count: number | null;
  preview_ready: boolean;
  created_at: string;
};

export type JobState =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export type JobRecord = {
  job_id: string;
  video_id: string;
  state: JobState;
  stage: string | null;
  processed_frames: number;
  total_frames: number | null;
  error_code: string | null;
  error: string | null;
  summary_status: string | null;
  created_at: string;
  cancel_requested: boolean;
  config: {
    render_annotated_video?: boolean;
    counting?: { lines?: { line_id?: string }[] };
  };
};

export type JobPage = {
  items: JobRecord[];
  total: number;
  limit: number;
  offset: number;
};

export type CatalogModel = {
  model_id: string;
  classes: { id: number; name: string }[];
};

export type Catalog = {
  models: CatalogModel[];
  tracker_configs: { tracker_config_id: string }[];
};

export type ProcessingDefaults = {
  render_annotated_video: boolean;
  start_s: number;
  end_s: number | null;
  detector: { confidence: number; classes: string[] };
  tracker: {
    track_buffer: number;
    match_thresh: number;
    track_low_thresh: number;
  };
};

export type TablePage = {
  items: Record<string, string>[];
  total: number;
  limit: number;
  offset: number;
};
