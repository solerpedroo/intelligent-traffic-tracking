"use client";

import { useEffect, useState } from "react";
import { ApiHealth } from "@/components/api-health";
import { ButtonLink } from "@/components/ui/button";
import { ApiError, fetchJobs } from "@/lib/api";
import type { JobRecord } from "@/types/api";

export default function HomePage() {
  const [jobs, setJobs] = useState<JobRecord[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchJobs(controller.signal)
      .then((page) => setJobs(page.items.slice(0, 5)))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof ApiError
              ? reason.message
              : "Recent jobs are unavailable.",
          );
        }
      });
    return () => controller.abort();
  }, []);

  const counts = countStates(jobs ?? []);

  return (
    <main className="flex flex-col gap-16 pb-8 pt-4 sm:gap-20 sm:pt-10">
      <section aria-labelledby="title" className="flex flex-col gap-8">
        <div className="flex max-w-3xl flex-col gap-5">
          <p className="kicker">Intelligent Traffic Tracking</p>
          <h1
            id="title"
            className="text-4xl leading-[1.12] tracking-tight sm:text-6xl"
          >
            Understand movement.
            <br />
            Measure with evidence.
          </h1>
          <p className="intro text-base leading-7 sm:text-lg">
            Upload a fixed-camera video, draw counting lines, and inspect the
            job that the local worker publishes.
          </p>
        </div>
        <div className="flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
          <ApiHealth />
          <div className="actions">
            <ButtonLink href="/workspace" size="lg">
              Open workspace
            </ButtonLink>
            <ButtonLink href="/jobs" variant="secondary" size="lg">
              View jobs
            </ButtonLink>
          </div>
        </div>
      </section>
      <section
        aria-labelledby="recent-title"
        className="surface-raised flex flex-col gap-6 p-6 sm:p-8"
      >
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <h2 id="recent-title" className="text-xl">
            Recent jobs
          </h2>
          {jobs && jobs.length > 0 ? (
            <ul className="flex flex-wrap gap-2">
              <li className="rounded-full border border-border px-3 py-1 text-sm text-muted-foreground">
                {counts.completed} completed
              </li>
              <li className="rounded-full border border-border px-3 py-1 text-sm text-muted-foreground">
                {counts.active} active
              </li>
              <li className="rounded-full border border-border px-3 py-1 text-sm text-muted-foreground">
                {counts.failed} failed or cancelled
              </li>
            </ul>
          ) : null}
        </div>
        {error ? <p role="alert">{error}</p> : null}
        {jobs && jobs.length === 0 ? (
          <p className="text-muted-foreground">No jobs yet.</p>
        ) : null}
        {jobs && jobs.length > 0 ? (
          <ul className="flex flex-col gap-3">
            {jobs.map((job) => (
              <li key={job.job_id}>
                <ButtonLink
                  href={`/jobs/${job.job_id}`}
                  variant="secondary"
                  className="h-auto w-full justify-between px-4 py-4"
                >
                  <span className="font-mono">{job.job_id.slice(0, 8)}</span>
                  <span className="capitalize">{job.state}</span>
                </ButtonLink>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </main>
  );
}

function countStates(jobs: JobRecord[]) {
  return {
    completed: jobs.filter((job) => job.state === "completed").length,
    active: jobs.filter(
      (job) => job.state === "queued" || job.state === "running",
    ).length,
    failed: jobs.filter(
      (job) => job.state === "failed" || job.state === "cancelled",
    ).length,
  };
}
