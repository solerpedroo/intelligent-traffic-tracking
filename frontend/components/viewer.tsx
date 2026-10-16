"use client";

import { useEffect, useMemo, useState } from "react";
import { ButtonLink, buttonClassName } from "@/components/ui/button";
import {
  ApiError,
  artifactUrl,
  fetchJob,
  fetchTable,
  fetchVideo,
} from "@/lib/api";
import { pollUntilTerminal } from "@/lib/polling";
import type { JobRecord, TablePage, VideoRecord } from "@/types/api";

const DOWNLOADS = [
  ["summary.json", "Summary JSON"],
  ["crossing_events.csv", "Crossing events CSV"],
  ["tracks.csv", "Tracks CSV"],
  ["trajectories.csv", "Trajectories CSV"],
  ["config.json", "Resolved config"],
  ["manifest.json", "Run manifest"],
  ["video.mp4", "Annotated video"],
] as const;

export function Viewer({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<JobRecord | null>(null);
  const [video, setVideo] = useState<VideoRecord | null>(null);
  const [events, setEvents] = useState<TablePage | null>(null);
  const [tracks, setTracks] = useState<TablePage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [classFilter, setClassFilter] = useState("");
  const [trackFilter, setTrackFilter] = useState("");
  const [videoMissing, setVideoMissing] = useState(false);

  useEffect(() => {
    let active = true;
    pollUntilTerminal(
      async () => {
        const next = await fetchJob(jobId);
        if (active) setJob(next);
        return next;
      },
      {
        intervalMs: 2000,
        shouldContinue: () => active,
        wait: (ms) => new Promise((resolve) => window.setTimeout(resolve, ms)),
      },
    ).catch((reason: unknown) => {
      if (active && !(reason instanceof DOMException)) {
        setError(
          reason instanceof ApiError
            ? reason.message
            : "API unavailable — check the local server and API URL.",
        );
      }
    });
    return () => {
      active = false;
    };
  }, [jobId]);

  useEffect(() => {
    // The explicit null check narrows `job` for the requests below.
    // biome-ignore lint/complexity/useOptionalChain: narrowing requires the null check
    if (!job || job.state !== "completed") return;
    const controller = new AbortController();
    Promise.all([
      fetchVideo(job.video_id, controller.signal),
      fetchTable(jobId, "events", controller.signal),
      fetchTable(jobId, "tracks", controller.signal),
    ])
      .then(([nextVideo, nextEvents, nextTracks]) => {
        setVideo(nextVideo);
        setEvents(nextEvents);
        setTracks(nextTracks);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof ApiError
              ? reason.message
              : "API unavailable — check the local server and API URL.",
          );
        }
      });
    return () => controller.abort();
  }, [job, jobId]);

  const visibleEvents = useMemo(
    () => filterRows(events?.items ?? [], classFilter, trackFilter),
    [events, classFilter, trackFilter],
  );
  const visibleTracks = useMemo(
    () =>
      filterRows(tracks?.items ?? [], classFilter, trackFilter).slice(0, 50),
    [tracks, classFilter, trackFilter],
  );
  const duration = video?.duration_s ?? maxTimestamp(visibleEvents);

  return (
    <main>
      <h1>Tracking viewer</h1>
      <p>
        <ButtonLink href="/jobs" variant="ghost" size="sm">
          Back to jobs
        </ButtonLink>
      </p>
      {error ? <p role="alert">{error}</p> : null}
      {!job ? <p role="status">Loading job…</p> : null}
      {job?.state === "completed" ? (
        <p>
          <ButtonLink href={`/analytics?job=${job.job_id}`} variant="secondary">
            Open analytics for this job
          </ButtonLink>
        </p>
      ) : null}
      {job ? (
        <p role="status" aria-live="polite">
          {job.state}
          {job.stage ? ` · ${job.stage}` : ""} · {job.processed_frames}
          {job.total_frames == null ? "" : ` / ${job.total_frames}`} frames
        </p>
      ) : null}
      {job?.state === "failed" || job?.state === "cancelled" ? (
        <p role="alert">
          {job.error_code ?? "stopped"}:{" "}
          {job.error ?? "This job did not complete."}
        </p>
      ) : null}
      {job?.state === "completed" &&
      job.config.render_annotated_video &&
      !videoMissing ? (
        <video
          controls
          src={artifactUrl(job.job_id, "video.mp4")}
          onError={() => setVideoMissing(true)}
        >
          <track kind="captions" />
          Annotated video for this job.
        </video>
      ) : null}
      {job?.state === "completed" && !job.config.render_annotated_video ? (
        <p>
          Annotated video was not requested. Numeric exports are still
          available.
        </p>
      ) : null}
      {videoMissing ? (
        <p>
          Annotated video is not available. Other exports remain listed below.
        </p>
      ) : null}
      {job?.state === "completed" ? (
        <>
          <section aria-labelledby="timeline-title">
            <h2 id="timeline-title">Crossing timeline</h2>
            <p>Times use the original media clock, in seconds.</p>
            <ul className="timeline">
              {visibleEvents.map((row) => {
                const time = Number(
                  row.timestamp_s ?? row.confirmation_s ?? "",
                );
                const width =
                  duration && Number.isFinite(time)
                    ? `${(time / duration) * 100}%`
                    : "0%";
                return (
                  <li
                    key={`${row.line_id}-${row.track_id}-${row.frame_index}-${row.timestamp_s}`}
                  >
                    <span className="tick" style={{ width }} />
                    {Number.isFinite(time) ? `${time}s` : "time unavailable"} ·
                    line {row.line_id ?? "—"} · class {row.class_id ?? "—"} ·
                    track {row.track_id ?? "—"} · {row.direction ?? "—"}
                  </li>
                );
              })}
            </ul>
            {events && events.total > events.items.length ? (
              <p>
                Showing the first {events.items.length} of {events.total}{" "}
                events.
              </p>
            ) : null}
          </section>
          <section aria-labelledby="filters-title">
            <h2 id="filters-title">Filters</h2>
            <label>
              Class ID
              <input
                value={classFilter}
                onChange={(event) => setClassFilter(event.target.value)}
              />
            </label>
            <label>
              Track ID
              <input
                value={trackFilter}
                onChange={(event) => setTrackFilter(event.target.value)}
              />
            </label>
            <table>
              <caption>
                Track rows from this job. Boxes stay in original pixels.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Time (s)</th>
                  <th scope="col">Track</th>
                  <th scope="col">Class</th>
                  <th scope="col">State</th>
                </tr>
              </thead>
              <tbody>
                {visibleTracks.map((row) => (
                  <tr
                    key={`${row.track_id}-${row.frame_index}-${row.timestamp_s}`}
                  >
                    <td>{row.timestamp_s ?? ""}</td>
                    <td>{row.track_id ?? ""}</td>
                    <td>{row.class_id ?? ""}</td>
                    <td>{row.state ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
          <section aria-labelledby="downloads-title">
            <h2 id="downloads-title">Downloads</h2>
            <ul>
              {DOWNLOADS.map(([name, label]) => (
                <li key={name}>
                  <a
                    className={buttonClassName("secondary", "sm")}
                    href={artifactUrl(job.job_id, name)}
                  >
                    {label}
                  </a>
                </li>
              ))}
            </ul>
          </section>
          <p>
            <ButtonLink href={`/workspace?video=${job.video_id}`}>
              Reprocess this video as a new job
            </ButtonLink>
          </p>
        </>
      ) : null}
    </main>
  );
}

function filterRows(
  rows: Record<string, string>[],
  classFilter: string,
  trackFilter: string,
) {
  return rows.filter((row) => {
    const classOk = classFilter === "" || (row.class_id ?? "") === classFilter;
    const trackOk = trackFilter === "" || (row.track_id ?? "") === trackFilter;
    return classOk && trackOk;
  });
}

function maxTimestamp(rows: Record<string, string>[]): number | null {
  const values = rows
    .map((row) => Number(row.timestamp_s ?? row.confirmation_s ?? ""))
    .filter((value) => Number.isFinite(value));
  if (values.length === 0) return null;
  return Math.max(...values);
}
