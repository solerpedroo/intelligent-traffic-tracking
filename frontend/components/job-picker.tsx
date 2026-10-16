"use client";

import { useEffect, useState } from "react";
import { ApiError, fetchJobs } from "@/lib/api";
import type { JobRecord } from "@/types/api";

export function useCompletedJobs() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchJobs(controller.signal)
      .then((page) =>
        setJobs(page.items.filter((job) => job.state === "completed")),
      )
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
  }, []);

  return { jobs, error };
}

export function JobSelect({
  label,
  jobs,
  value,
  onChange,
}: {
  label: string;
  jobs: JobRecord[];
  value: string;
  onChange: (jobId: string) => void;
}) {
  return (
    <label>
      {label}
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Select a completed job</option>
        {jobs.map((job) => (
          <option key={job.job_id} value={job.job_id}>
            {job.job_id.slice(0, 8)} · {job.video_id.slice(0, 8)}
          </option>
        ))}
      </select>
    </label>
  );
}
