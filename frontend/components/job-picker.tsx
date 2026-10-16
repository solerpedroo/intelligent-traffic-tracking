"use client";

import { useEffect, useState } from "react";
import { LabeledSelect } from "@/components/ui/select";
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

export function jobOptionLabel(jobId: string): string {
  return `${jobId.slice(0, 8)} · ${jobId}`;
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
    <LabeledSelect
      label={label}
      value={value}
      placeholder="Select a completed job"
      onChange={onChange}
      options={jobs.map((job) => ({
        value: job.job_id,
        label: jobOptionLabel(job.job_id),
      }))}
    />
  );
}
