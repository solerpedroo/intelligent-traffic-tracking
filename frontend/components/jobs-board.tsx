"use client";

import { useEffect, useState } from "react";
import { Button, ButtonLink } from "@/components/ui/button";
import { ApiError, cancelJob, fetchJobs } from "@/lib/api";
import { shouldKeepPolling } from "@/lib/polling";
import type { JobRecord } from "@/types/api";

export function JobsBoard() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer = 0;
    const load = async () => {
      try {
        const page = await fetchJobs();
        if (!active) return;
        setJobs(page.items);
        setError(null);
        if (shouldKeepPolling(page.items.map((job) => job.state))) {
          timer = window.setTimeout(load, 2000);
        }
      } catch (reason) {
        if (!active) return;
        setError(
          reason instanceof ApiError
            ? reason.message
            : "API unavailable — check the local server and API URL.",
        );
      }
    };
    void load();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, []);

  async function onCancel(jobId: string) {
    try {
      const updated = await cancelJob(jobId);
      setJobs((current) =>
        current.map((job) => (job.job_id === jobId ? updated : job)),
      );
      setError(null);
    } catch (reason) {
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
