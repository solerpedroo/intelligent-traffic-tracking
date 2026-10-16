"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { GeometryEditor } from "@/components/geometry-editor";
import { Button, ButtonLink } from "@/components/ui/button";
import { LabeledSelect } from "@/components/ui/select";
import {
  ApiError,
  createJob,
  fetchCatalog,
  fetchProcessingDefaults,
  fetchVideo,
  uploadVideo,
} from "@/lib/api";
import {
  blankLine,
  blankZone,
  type JobDraft,
  toJobBody,
  validateDraft,
} from "@/lib/job-draft";
import type { Catalog, ProcessingDefaults, VideoRecord } from "@/types/api";

export function Workspace() {
  const params = useSearchParams();
  const requestedVideo = params.get("video");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [classNames, setClassNames] = useState<string[]>([]);
  const [draft, setDraft] = useState<JobDraft | null>(null);
  const [video, setVideo] = useState<VideoRecord | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetchCatalog(controller.signal),
      fetchProcessingDefaults(controller.signal),
    ])
      .then(([nextCatalog, defaults]) => {
        setCatalog(nextCatalog);
        setClassNames(defaults.detector.classes.slice());
        setDraft(draftFrom(defaults, nextCatalog));
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(problem(reason));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!requestedVideo) return;
    const controller = new AbortController();
    fetchVideo(requestedVideo, controller.signal)
      .then((record) => {
        setVideo(record);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(problem(reason));
      });
    return () => controller.abort();
  }, [requestedVideo]);

  async function onUpload() {
    if (!file) {
      setError("Choose a video file first.");
      return;
    }
    setError(null);
    try {
      const record = await uploadVideo(file);
      setVideo(record);
      setMessage(`Uploaded ${record.filename}.`);
    } catch (reason) {
      setError(problem(reason));
    }
  }

  async function onStart(event: React.FormEvent) {
    event.preventDefault();
    if (!draft) return;
    if (!video) {
      setError("Upload a video before starting a job.");
      return;
    }
    const invalid = validateDraft(draft);
    if (invalid) {
      setError(invalid);
      setMessage(null);
      return;
    }
    setError(null);
    try {
      const created = await createJob(toJobBody(video.video_id, draft));
      setJobId(created.job_id);
      setMessage(`Job ${created.job_id} is ${created.state}.`);
    } catch (reason) {
      setJobId(null);
      setError(problem(reason));
    }
  }

  return (
    <main>
      <h1>Video workspace</h1>
      <p className="intro">
        Upload one video, place counting lines and zones on the original frame,
        then queue a job. The API does not run the model in this request.
      </p>
      {loading ? <p role="status">Loading catalog…</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {message ? <p role="status">{message}</p> : null}
      <section className="panel" aria-labelledby="upload-title">
        <h2 id="upload-title">Upload</h2>
        <label>
          Video file
          <input
            type="file"
            accept="video/mp4,video/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <Button type="button" onClick={onUpload}>
          Upload
        </Button>
        {video ? (
          <p>
            {video.filename} · {video.width}×{video.height}
            {video.duration_s == null ? "" : ` · ${video.duration_s}s`}
          </p>
        ) : (
          <p>No video uploaded yet.</p>
        )}
      </section>
      {draft && catalog ? (
        <form className="panel" onSubmit={onStart}>
          <h2>Configuration</h2>
          <LabeledSelect
            label="Detector"
            value={draft.detectorModelId}
            placeholder="None"
            onChange={(detectorModelId) =>
              setDraft({ ...draft, detectorModelId })
            }
            options={catalog.models.map((model) => ({
              value: model.model_id,
              label: model.model_id,
            }))}
          />
          <LabeledSelect
            label="Tracker"
            value={draft.trackerConfigId}
            placeholder="None"
            onChange={(trackerConfigId) =>
              setDraft({ ...draft, trackerConfigId })
            }
            options={catalog.tracker_configs.map((preset) => ({
              value: preset.tracker_config_id,
              label: preset.tracker_config_id,
            }))}
          />
          <fieldset>
            <legend>Classes</legend>
            {classNames.length === 0 ? (
              <p>No classes in the server defaults.</p>
            ) : null}
            {classNames.map((name) => (
              <label key={name}>
                <input
                  type="checkbox"
                  checked={draft.classes.includes(name)}
                  onChange={(event) => {
                    const classes = event.target.checked
                      ? [...draft.classes, name]
                      : draft.classes.filter((item) => item !== name);
                    setDraft({ ...draft, classes });
                  }}
                />
                {name}
              </label>
            ))}
          </fieldset>
          <label>
            Start time (s)
            <input
              type="number"
              min={0}
              step={0.1}
              value={draft.startS}
              onChange={(event) =>
                setDraft({ ...draft, startS: event.target.value })
              }
            />
          </label>
          <label>
            End time (s)
            <input
              type="number"
              min={0}
              step={0.1}
              value={draft.endS}
              placeholder="End of video"
              onChange={(event) =>
                setDraft({ ...draft, endS: event.target.value })
              }
            />
          </label>
          <label>
            Detection confidence
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={draft.confidence}
              onChange={(event) =>
                setDraft({ ...draft, confidence: event.target.value })
              }
            />
          </label>
          <label>
            Track buffer
            <input
              type="number"
              min={1}
              max={300}
              step={1}
              value={draft.trackBuffer}
              onChange={(event) =>
                setDraft({ ...draft, trackBuffer: event.target.value })
              }
            />
          </label>
          <label>
            Match threshold
            <input
              type="number"
              min={0}
              max={1}
              step={0.01}
              value={draft.matchThresh}
              onChange={(event) =>
                setDraft({ ...draft, matchThresh: event.target.value })
              }
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={draft.renderAnnotatedVideo}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  renderAnnotatedVideo: event.target.checked,
                })
              }
            />
            Render annotated video
          </label>
          <div className="actions">
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                setDraft({
                  ...draft,
                  lines: [...draft.lines, blankLine(draft.lines.length)],
                })
              }
            >
              Add line
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                setDraft({
                  ...draft,
                  zones: [...draft.zones, blankZone(draft.zones.length)],
                })
              }
            >
              Add zone
            </Button>
          </div>
          {video ? (
            <GeometryEditor
              videoId={video.video_id}
              previewReady={video.preview_ready}
              frameWidth={video.width}
              frameHeight={video.height}
              lines={draft.lines}
              zones={draft.zones}
              onChangeLine={(index, line) => {
                const lines = draft.lines.slice();
                lines[index] = line;
                setDraft({ ...draft, lines });
              }}
              onChangeZone={(index, zone) => {
                const zones = draft.zones.slice();
                zones[index] = zone;
                setDraft({ ...draft, zones });
              }}
            />
          ) : null}
          <Button type="submit">Start job</Button>
          {jobId ? (
            <p>
              <ButtonLink href={`/jobs/${jobId}`} variant="secondary">
                Open this job in the viewer
              </ButtonLink>
            </p>
          ) : null}
        </form>
      ) : null}
    </main>
  );
}

function draftFrom(defaults: ProcessingDefaults, catalog: Catalog): JobDraft {
  return {
    detectorModelId: catalog.models[0]?.model_id ?? "",
    trackerConfigId: catalog.tracker_configs[0]?.tracker_config_id ?? "",
    renderAnnotatedVideo: defaults.render_annotated_video,
    startS: String(defaults.start_s),
    endS: defaults.end_s == null ? "" : String(defaults.end_s),
    classes: defaults.detector.classes.slice(),
    confidence: String(defaults.detector.confidence),
    trackBuffer: String(defaults.tracker.track_buffer),
    matchThresh: String(defaults.tracker.match_thresh),
    lines: [],
    zones: [],
  };
}

function problem(reason: unknown): string {
  if (reason instanceof ApiError) return reason.message;
  return "API unavailable — check the local server and API URL.";
}
