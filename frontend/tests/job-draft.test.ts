import { describe, expect, it } from "vitest";
import {
  blankLine,
  type JobDraft,
  toJobBody,
  validateDraft,
} from "@/lib/job-draft";

function draft(overrides: Partial<JobDraft> = {}): JobDraft {
  return {
    detectorModelId: "yolo11n-coco",
    trackerConfigId: "bytetrack-default",
    renderAnnotatedVideo: true,
    startS: "0",
    endS: "",
    classes: ["person", "car"],
    confidence: "0.1",
    trackBuffer: "30",
    matchThresh: "0.8",
    lines: [],
    zones: [],
    ...overrides,
  };
}

describe("job draft", () => {
  it("rejects an end time that is not after the start", () => {
    expect(validateDraft(draft({ endS: "0" }))).toMatch(/End time/);
  });

  it("rejects a confidence outside the unit interval", () => {
    expect(validateDraft(draft({ confidence: "1.2" }))).toMatch(/confidence/);
  });

  it("rejects a line without a tracker", () => {
    expect(
      validateDraft(draft({ trackerConfigId: "", lines: [blankLine(0)] })),
    ).toMatch(/tracker/);
  });

  it("serializes normalized line endpoints", () => {
    const body = toJobBody("video-1", draft({ lines: [blankLine(0)] }));
    expect(body).toMatchObject({
      video_id: "video-1",
      counting: {
        lines: [{ line_id: "line-1", start: [0.2, 0.5], end: [0.8, 0.5] }],
      },
    });
  });
});
