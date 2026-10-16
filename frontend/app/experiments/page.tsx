"use client";

import { useState } from "react";
import { ComparisonView } from "@/components/comparison-view";
import { JobSelect, useCompletedJobs } from "@/components/job-picker";

export default function ExperimentsPage() {
  const { jobs, error } = useCompletedJobs();
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");

  return (
    <main>
      <h1>Experiment comparison</h1>
      <p className="intro">
        Side-by-side runs are a controlled comparison only when the video,
        interval, geometry, weights, tracker settings, and hardware match.
      </p>
      {error ? <p role="alert">{error}</p> : null}
      <div className="actions">
        <JobSelect
          label="Left job"
          jobs={jobs}
          value={left}
          onChange={setLeft}
        />
        <JobSelect
          label="Right job"
          jobs={jobs}
          value={right}
          onChange={setRight}
        />
      </div>
      {left && right && left !== right ? (
        <ComparisonView
          key={`${left}:${right}`}
          leftId={left}
          rightId={right}
        />
      ) : (
        <p>Select two different completed jobs.</p>
      )}
    </main>
  );
}
