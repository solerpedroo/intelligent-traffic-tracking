"use client";

import { useEffect, useRef, useState } from "react";
import { Button, ButtonLink } from "@/components/ui/button";
import { ApiError, cancelJob, fetchJobs } from "@/lib/api";
import { shouldKeepPolling } from "@/lib/polling";
import type { JobRecord } from "@/types/api";

export function JobsBoard() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const jobsRef = useRef<JobRecord[]>([]);
  const requestSerial = useRef(0);
  const finishedSerial = useRef(0);
  const scheduleRef = useRef<(() => void) | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    let active = true;
    let timer = 0;
    const controller = new AbortController();
    mountedRef.current = true;

    const arm = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        void load();
      }, 2000);
    };
    scheduleRef.current = arm;

    const applyJobs = (next: JobRecord[]) => {
      jobsRef.current = next;
      setJobs(next);
    };

    async function load() {
      const serial = ++requestSerial.current;
      try {
        const page = await fetchJobs(controller.signal);
        if (!active) return;
        if (serial < finishedSerial.current) {
          if (shouldKeepPolling(jobsRef.current.map((job) => job.state))) {
            arm();
          }
          return;
        }
        finishedSerial.current = serial;
        applyJobs(page.items);
        setError(null);
        if (shouldKeepPolling(page.items.map((job) => job.state))) arm();
      } catch (reason) {
        if (!active || controller.signal.aborted) return;
        if (serial < finishedSerial.current) {
          if (shouldKeepPolling(jobsRef.current.map((job) => job.state))) {
            arm();
          }
          return;
        }
        finishedSerial.current = serial;
        setError(
          reason instanceof ApiError
            ? reason.message
            : "API unavailable — check the local server and API URL.",
        );
        arm();
      }
    }

    void load();
    return () => {
      active = false;
      mountedRef.current = false;
      scheduleRef.current = null;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, []);

  async function onCancel(jobId: string) {
    const serial = ++requestSerial.current;
    try {
      const updated = await cancelJob(jobId);
      if (!mountedRef.current) return;
      finishedSerial.current = Math.max(finishedSerial.current, serial);
      const next = jobsRef.current.map((job) =>
        job.job_id === jobId ? updated : job,
      );
      jobsRef.current = next;
      setJobs(next);
      setError(null);
      if (shouldKeepPolling(next.map((job) => job.state))) {
        scheduleRef.current?.();
      }
    } catch (reason) {
      if (!mountedRef.current || serial < finishedSerial.current) return;
      setError(
        reason instanceof ApiError
          ? reason.message
          : "API unavailable — check the local server and API URL.",
      );
    }
  }

  return (
    <main>
      <h1>Processing jobs</h1>
      <p className="intro">
        One worker claims one job at a time. Queued jobs cancel immediately.
        Running jobs stop at the next frame.
      </p>
      {error ? <p role="alert">{error}</p> : null}
      {jobs.length === 0 ? (
        <p>
          No jobs yet.{" "}
          <ButtonLink href="/workspace">Open the workspace</ButtonLink> to
          upload a video.
        </p>
      ) : (
        <table>
          <caption>Jobs stored for this local API</caption>
          <thead>
            <tr>
              <th scope="col">Job</th>
              <th scope="col">State</th>
              <th scope="col">Progress</th>
              <th scope="col">Action</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.job_id}>
                <td>
                  <ButtonLink
                    href={`/jobs/${job.job_id}`}
                    variant="ghost"
                    size="sm"
                  >
                    {job.job_id.slice(0, 8)}
                  </ButtonLink>
                </td>
                <td>
                  {job.state}
                  {job.stage ? ` · ${job.stage}` : ""}
                </td>
                <td>
                  {job.processed_frames}
                  {job.total_frames == null ? "" : ` / ${job.total_frames}`}{" "}
                  frames
                </td>
                <td>
                  {job.state === "queued" || job.state === "running" ? (
                    <Button
                      type="button"
                      variant="destructive"
                      size="sm"
                      onClick={() => onCancel(job.job_id)}
                    >
                      Cancel
                    </Button>
                  ) : (
                    <ButtonLink
                      href={`/jobs/${job.job_id}`}
                      variant="secondary"
                      size="sm"
                    >
                      Open viewer
                    </ButtonLink>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
