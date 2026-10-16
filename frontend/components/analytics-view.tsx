"use client";

import { useEffect, useState } from "react";
import { Bars, MetricNote } from "@/components/metric-block";
import { type AnalyticsReport, buildAnalytics } from "@/lib/analytics";
import {
  ApiError,
  fetchArtifactText,
  fetchCatalog,
  fetchJob,
  heatmapPreviewUrl,
} from "@/lib/api";

export function AnalyticsView({ jobId }: { jobId: string }) {
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    loadReport(jobId, controller.signal)
      .then((next) => {
        setReport(next);
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
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [jobId]);

  if (loading) return <p role="status">Loading artifacts…</p>;
  if (error) return <p role="alert">{error}</p>;
  if (!report) return null;
  return <AnalyticsSections jobId={jobId} report={report} />;
}

function AnalyticsSections({
  jobId,
  report,
}: {
  jobId: string;
  report: AnalyticsReport;
}) {
  return (
    <>
      <section aria-labelledby="counts-title">
        <h2 id="counts-title">Counts</h2>
        <p>Unit: crossing events confirmed for this job.</p>
        <MetricNote metric={report.counts} />
        {report.counts.total != null ? (
          <p>{report.counts.total} events in summary.json</p>
        ) : null}
        <Bars
          unit="events"
          items={report.counts.bars.map((bar) => ({
            key: bar.key,
            label: bar.label,
            value: bar.count,
          }))}
        />
      </section>
      <section aria-labelledby="series-title">
        <h2 id="series-title">Series</h2>
        <p>{report.series.windowNote}</p>
        <MetricNote metric={report.series} />
        <Bars
          unit="events"
          items={report.series.points.map((point) => ({
            key: point.key,
            label: `${point.startS}–${point.endS} s`,
            value: point.count,
          }))}
        />
      </section>
      <section aria-labelledby="occupancy-title">
        <h2 id="occupancy-title">Zone occupancy</h2>
        <p>Unit: tracks observed inside the zone on one original frame.</p>
        <MetricNote metric={report.occupancy} />
        <table>
          <caption>Maximum and mean occupancy from zone_occupancy.csv</caption>
          <thead>
            <tr>
              <th scope="col">Zone</th>
              <th scope="col">Maximum</th>
              <th scope="col">Mean</th>
              <th scope="col">Frames</th>
            </tr>
          </thead>
          <tbody>
            {report.occupancy.bars.map((bar) => (
              <tr key={bar.key}>
                <td>{bar.label}</td>
                <td>{bar.maximum}</td>
                <td>{bar.mean.toFixed(2)}</td>
                <td>{bar.frames}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section aria-labelledby="tracks-title">
        <h2 id="tracks-title">Track duration</h2>
        <p>
          Unit: seconds from the first to the last consecutive observation. This
          is not physical dwell outside the camera.
        </p>
        <MetricNote metric={report.tracks} />
        <ul>
          {report.tracks.spans.slice(0, 20).map((span) => (
            <li key={`${span.trackId}-${span.classLabel}`}>
              Track {span.trackId} · {span.classLabel} · {span.spanS} s ·{" "}
              {span.observations} observations · {span.closure || "open"}
              {span.eligible ? "" : " · not eligible for analysis"}
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="heatmap-title">
        <h2 id="heatmap-title">Heatmaps</h2>
        <MetricNote metric={report.heatmaps} />
        <ul className="heatmap-list">
          {report.heatmaps.cards.map((card) => (
            <li key={card.key}>
              <p>
                {card.classLabel} · {card.windowStartS}–{card.windowEndS} s ·{" "}
                {card.observations} {card.unit}
              </p>
              {card.previewName ? (
                // The preview is a job artifact, not a static Next image.
                // biome-ignore lint/performance/noImgElement: remote job PNG
                <img
                  src={heatmapPreviewUrl(jobId, card.previewName)}
                  alt={`Heatmap preview for ${card.classLabel}`}
                />
              ) : (
                <p>No preview file was published for this window.</p>
              )}
            </li>
          ))}
        </ul>
      </section>
      <section aria-labelledby="speed-title">
        <h2 id="speed-title">Performance</h2>
        <ul>
          <li>
            Elapsed: {showValue(report.performance.elapsedS.value, "s")}
            <MetricNote metric={report.performance.elapsedS} />
          </li>
          <li>
            End-to-end:{" "}
            {showValue(report.performance.endToEndFps.value, "frames/s")}
            <MetricNote metric={report.performance.endToEndFps} />
          </li>
          <li>
            Inference:{" "}
            {showValue(report.performance.inferenceFps.value, "forwards/s")}
            <MetricNote metric={report.performance.inferenceFps} />
          </li>
          <li>
            Mean inference:{" "}
            {showValue(report.performance.meanInferenceMs.value, "ms")}
            <MetricNote metric={report.performance.meanInferenceMs} />
          </li>
        </ul>
      </section>
      <section aria-labelledby="fragmentation-title">
        <h2 id="fragmentation-title">Fragmentation</h2>
        <MetricNote metric={report.fragmentation} />
        {report.fragmentation.suspectedLosses.length === 0 ? (
          <p>No observation_lost closures are in the lifetime export.</p>
        ) : (
          <ul>
            {report.fragmentation.suspectedLosses.map((span) => (
              <li key={`lost-${span.trackId}`}>
                Suspected loss, not a confirmed ID switch: track {span.trackId}{" "}
                closed as observation_lost after {span.spanS} s.
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}

async function loadReport(jobId: string, signal: AbortSignal) {
  const [job, catalog, summaryText, windows, lifetimes, occupancy, heatmaps] =
    await Promise.all([
      fetchJob(jobId, signal),
      fetchCatalog(signal),
      fetchArtifactText(jobId, "summary.json", signal),
      fetchArtifactText(jobId, "crossing_windows.csv", signal),
      fetchArtifactText(jobId, "track-lifetimes.csv", signal),
      fetchArtifactText(jobId, "zone_occupancy.csv", signal),
      fetchArtifactText(jobId, "heatmap_index.csv", signal),
    ]);
  if (job.state !== "completed") {
    throw new ApiError(
      409,
      "job_not_completed",
      "Analytics are published only after the job completes.",
    );
  }
  return buildAnalytics({
    summary: summaryText ? JSON.parse(summaryText) : null,
    windowsText: windows,
    lifetimesText: lifetimes,
    occupancyText: occupancy,
    heatmapText: heatmaps,
    classes: catalog.models.flatMap((model) => model.classes),
  });
}

function showValue(value: number | null, unit: string): string {
  return value == null ? "not evaluated" : `${value} ${unit}`;
}
