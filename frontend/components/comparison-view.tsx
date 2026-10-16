"use client";

import { useEffect, useState } from "react";
import {
  type Comparison,
  compareRuns,
  type RunFacts,
  runFacts,
} from "@/lib/analytics";
import { ApiError, fetchArtifactText } from "@/lib/api";

export function ComparisonView({
  leftId,
  rightId,
}: {
  leftId: string;
  rightId: string;
}) {
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [facts, setFacts] = useState<[RunFacts, RunFacts] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      loadFacts(leftId, controller.signal),
      loadFacts(rightId, controller.signal),
    ])
      .then(([left, right]) => {
        setFacts([left, right]);
        setComparison(compareRuns(left, right));
        setError(null);
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
  }, [leftId, rightId]);

  if (error) return <p role="alert">{error}</p>;
  if (!comparison || !facts) return <p role="status">Comparing artifacts…</p>;
  return (
    <section aria-labelledby="comparison-title">
      <h2 id="comparison-title">Comparison</h2>
      <p role="status">{comparison.statement}</p>
      {comparison.differences.length > 0 ? (
        <ul>
          {comparison.differences.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      <table>
        <caption>
          Recorded inputs. Counts are not pooled across differences.
        </caption>
        <thead>
          <tr>
            <th scope="col">Input</th>
            <th scope="col">Left</th>
            <th scope="col">Right</th>
          </tr>
        </thead>
        <tbody>
          <Row label="Video" left={facts[0].videoId} right={facts[1].videoId} />
          <Row
            label="Interval (s)"
            left={formatInterval(facts[0])}
            right={formatInterval(facts[1])}
          />
          <Row
            label="Detector"
            left={facts[0].modelId ?? "none"}
            right={facts[1].modelId ?? "none"}
          />
          <Row
            label="Checkpoint"
            left={facts[0].checkpoint ?? "not recorded"}
            right={facts[1].checkpoint ?? "not recorded"}
          />
          <Row
            label="Tracker"
            left={facts[0].trackerId ?? "none"}
            right={facts[1].trackerId ?? "none"}
          />
          <Row
            label="Device"
            left={facts[0].device ?? "not recorded"}
            right={facts[1].device ?? "not recorded"}
          />
          <Row
            label="Hardware"
            left={facts[0].hardware ?? "not recorded"}
            right={facts[1].hardware ?? "not recorded"}
          />
        </tbody>
      </table>
    </section>
  );
}

function formatInterval(facts: RunFacts): string {
  if (facts.startS == null) return "not recorded";
  return `${facts.startS}–${facts.endS ?? "end"}`;
}

function Row({
  label,
  left,
  right,
}: {
  label: string;
  left: string;
  right: string;
}) {
  return (
    <tr>
      <th scope="row">{label}</th>
      <td>{left}</td>
      <td>{right}</td>
    </tr>
  );
}

async function loadFacts(
  jobId: string,
  signal: AbortSignal,
): Promise<RunFacts> {
  const [configText, manifestText] = await Promise.all([
    fetchArtifactText(jobId, "config.json", signal),
    fetchArtifactText(jobId, "manifest.json", signal),
  ]);
  if (!configText || !manifestText) {
    throw new ApiError(
      404,
      "artifact_missing",
      "Both config.json and manifest.json are required to compare runs.",
    );
  }
  return runFacts(jobId, JSON.parse(configText), JSON.parse(manifestText));
}
