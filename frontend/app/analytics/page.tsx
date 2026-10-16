"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AnalyticsView } from "@/components/analytics-view";
import { JobSelect, useCompletedJobs } from "@/components/job-picker";

export default function AnalyticsPage() {
  return (
    <Suspense
      fallback={
        <main>
          <p role="status">Loading analytics…</p>
        </main>
      }
    >
      <AnalyticsPageBody />
    </Suspense>
  );
}

function AnalyticsPageBody() {
  const params = useSearchParams();
  const requested = params.get("job") ?? "";
  const { jobs, error } = useCompletedJobs();
  const [selected, setSelected] = useState(requested);

  return (
    <main>
      <h1>Traffic analytics</h1>
      <p className="intro">
        Every number on this page is read from the job artifacts. A missing
        reference stays not evaluated and is never shown as zero.
      </p>
      {error ? <p role="alert">{error}</p> : null}
      <JobSelect
        label="Job"
        jobs={jobs}
        value={selected}
        onChange={setSelected}
      />
      {selected ? (
        <AnalyticsView key={selected} jobId={selected} />
      ) : (
        <p>Select a completed job to read its summary and exports.</p>
      )}
    </main>
  );
}
