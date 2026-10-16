import { describe, expect, it } from "vitest";
import {
  buildAnalytics,
  compareRuns,
  reconcileWindows,
  runFacts,
} from "@/lib/analytics";

const summary = {
  elapsed_s: 2,
  end_to_end_fps: 2,
  inference_fps: null,
  counting: {
    total_events: 2,
    by_line_class_direction: [
      { line_id: "gate", class_id: 2, direction: "A_TO_B", count: 2 },
    ],
    by_line_direction: [
      { line_id: "gate", direction: "A_TO_B", count: 2 },
      { line_id: "gate", direction: "B_TO_A", count: 0 },
    ],
  },
  tracker: { mot_evaluation: "not_evaluated_no_ground_truth" },
};

const windows = [
  "window_start_s,window_end_s,line_id,class_id,direction,count",
  "0,60,gate,2,A_TO_B,1",
  "60,120,gate,2,A_TO_B,1",
].join("\n");

describe("analytics artifacts", () => {
  it("reconciles window rows with the counting summary", () => {
    expect(reconcileWindows(summary, windows).ok).toBe(true);
    const report = buildAnalytics({
      summary,
      windowsText: windows,
      lifetimesText: null,
      occupancyText: null,
      heatmapText: null,
      classes: [{ id: 2, name: "car" }],
    });
    expect(report.counts.total).toBe(2);
    expect(report.counts.bars.map((bar) => bar.count)).toEqual([2, 0]);
    expect(report.series.points).toEqual([
      { key: "0-60", startS: 0, endS: 60, count: 1 },
      { key: "60-120", startS: 60, endS: 120, count: 1 },
    ]);
  });

  it("keeps an explicit zero on a short run and does not invent inference FPS", () => {
    const short = {
      selected_frames: 1,
      elapsed_s: 0.2,
      end_to_end_fps: 5,
      inference_fps: null,
      counting: {
        total_events: 0,
        by_line_class_direction: [],
        by_line_direction: [
          { line_id: "gate", direction: "A_TO_B", count: 0 },
          { line_id: "gate", direction: "B_TO_A", count: 0 },
        ],
      },
    };
    const report = buildAnalytics({
      summary: short,
      windowsText:
        "window_start_s,window_end_s,line_id,class_id,direction,count\n",
      lifetimesText: null,
      occupancyText: null,
      heatmapText: null,
      classes: [],
    });
    expect(report.counts.status).toBe("measured");
    expect(report.counts.total).toBe(0);
    expect(report.performance.inferenceFps.status).toBe("not_evaluated");
    expect(report.occupancy.status).toBe("not_evaluated");
  });

  it("does not turn missing ground truth into zero ID switches", () => {
    const report = buildAnalytics({
      summary,
      windowsText: null,
      lifetimesText: [
        "track_id,class_id,observed_span_s,observations,analysis_eligible,closure_reason",
        "7,2,1.5,4,True,observation_lost",
      ].join("\n"),
      occupancyText: null,
      heatmapText: null,
      classes: [],
    });
    expect(report.fragmentation.status).toBe("not_evaluated");
    expect(report.fragmentation.reason).toMatch(/not identity switches/);
    expect(report.fragmentation.suspectedLosses[0]?.trackId).toBe("7");
  });

  it("refuses to treat different videos as a controlled ablation", () => {
    const left = runFacts(
      "a",
      {
        video_id: "clip-a",
        start_s: 0,
        end_s: null,
        detector_model_id: "yolo11n-coco",
      },
      { hardware: "cpu-a", detector: { checkpoint_sha256: "abc" } },
    );
    const right = runFacts(
      "b",
      {
        video_id: "clip-b",
        start_s: 0,
        end_s: null,
        detector_model_id: "yolo11n-coco",
      },
      { hardware: "cpu-a", detector: { checkpoint_sha256: "abc" } },
    );
    const comparison = compareRuns(left, right);
    expect(comparison.controlled).toBe(false);
    expect(comparison.differences).toContain("Different videos");
    expect(comparison.statement).toMatch(/not a controlled ablation/);
  });
});
