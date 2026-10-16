"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiHealth } from "@/components/api-health";
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
    <main>
      <section aria-labelledby="title">
        <p className="kicker">Intelligent Traffic Tracking</p>
        <h1 id="title">
          Understand movement.
          <br />
          Measure with evidence.
        </h1>
        <p className="intro">
          Upload a fixed-camera video, draw counting lines, and inspect the job
          that the local worker publishes.
        </p>
        <ApiHealth />
        <p className="actions">
          <Link href="/workspace">Open workspace</Link>
          <Link href="/jobs">View jobs</Link>
        </p>
      </section>
      <section aria-labelledby="recent-title">
        <h2 id="recent-title">Recent jobs</h2>
        {error ? <p role="alert">{error}</p> : null}
        {jobs && jobs.length === 0 ? <p>No jobs yet.</p> : null}
        {jobs && jobs.length > 0 ? (
          <>
            <p>
              {counts.completed} completed · {counts.active} active ·{" "}
              {counts.failed} failed or cancelled
            </p>
            <ul>
              {jobs.map((job) => (
                <li key={job.job_id}>
                  <Link href={`/jobs/${job.job_id}`}>
                    {job.job_id.slice(0, 8)} · {job.state}
                  </Link>
                </li>
              ))}
            </ul>
          </>
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
