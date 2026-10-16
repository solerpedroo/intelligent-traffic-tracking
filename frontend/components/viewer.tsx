"use client";

import { useEffect, useMemo, useRef, useState } from "react";
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
  const [trackedJobId, setTrackedJobId] = useState(jobId);
  const jobIdRef = useRef(jobId);
  jobIdRef.current = jobId;
  if (trackedJobId !== jobId) {
    setTrackedJobId(jobId);
    setJob(null);
    setVideo(null);
    setEvents(null);
    setTracks(null);
    setError(null);
    setClassFilter("");
    setTrackFilter("");
    setVideoMissing(false);
  }

  useEffect(() => {
    let active = true;
    let timer = 0;
    let finishWait: (() => void) | null = null;
    const controller = new AbortController();
    const stopWait = () => {
      window.clearTimeout(timer);
      const finish = finishWait;
      finishWait = null;
      finish?.();
    };
    pollUntilTerminal(
      async () => {
        const next = await fetchJob(jobId, controller.signal);
        if (active && jobIdRef.current === jobId) setJob(next);
        return next;
      },
      {
        intervalMs: 2000,
        shouldContinue: () => active && jobIdRef.current === jobId,
        wait: (ms) =>
          new Promise((resolve) => {
            finishWait = () => {
              finishWait = null;
              resolve();
            };
            timer = window.setTimeout(() => {
              finishWait = null;
              resolve();
            }, ms);
          }),
      },
    ).catch((reason: unknown) => {
      if (!active || jobIdRef.current !== jobId) return;
      if (reason instanceof DOMException) return;
      setError(
        reason instanceof ApiError
          ? reason.message
          : "API unavailable — check the local server and API URL.",
      );
    });
    return () => {
      active = false;
      controller.abort();
      stopWait();
    };
  }, [jobId]);

  useEffect(() => {
    // The explicit null check narrows `job` for the requests below.
    // biome-ignore lint/complexity/useOptionalChain: narrowing requires the null check
    if (!job || job.state !== "completed") return;
    const controller = new AbortController();
    let cancelled = false;
    Promise.all([
      fetchVideo(job.video_id, controller.signal),
      fetchTable(jobId, "events", controller.signal),
      fetchTable(jobId, "tracks", controller.signal),
    ])
      .then(([nextVideo, nextEvents, nextTracks]) => {
        if (cancelled || controller.signal.aborted) return;
        if (jobIdRef.current !== jobId) return;
        setVideo(nextVideo);
        setEvents(nextEvents);
        setTracks(nextTracks);
      })
      .catch((reason: unknown) => {
        if (cancelled || controller.signal.aborted) return;
        if (jobIdRef.current !== jobId) return;
        setError(
          reason instanceof ApiError
            ? reason.message
            : "API unavailable — check the local server and API URL.",
        );
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [job, jobId]);

  const visibleEvents = useMemo(
    () => filterRows(events?.items ?? [], classFilter, trackFilter),
    [events, classFilter, trackFilter],
  );
  const visibleTracks = useMemo(
    () => filterRows(tracks?.items ?? [], classFilter, trackFilter),
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
                Showing {events.items.length} loaded events of {events.total}.
                Filters cover the loaded rows only, not the rest of the file.
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
            {coverageNote(events, "events")}
            {coverageNote(tracks, "tracks")}
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

function coverageNote(page: TablePage | null, noun: string) {
  if (page == null || page.total <= page.items.length) return null;
  return (
    <p>
      The {noun} filter covers the {page.items.length} loaded rows only, not all{" "}
      {page.total}.
    </p>
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
