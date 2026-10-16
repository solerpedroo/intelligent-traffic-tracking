import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Suspense } from "react";
import { beforeEach, expect, it, vi } from "vitest";
import { Workspace } from "@/components/workspace";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

const defaults = {
  render_annotated_video: true,
  start_s: 0,
  end_s: null,
  detector: { confidence: 0.1, classes: ["person", "car"] },
  tracker: { track_buffer: 30, match_thresh: 0.8, track_low_thresh: 0.1 },
};

const catalog = {
  models: [{ model_id: "yolo11n-coco", classes: [{ id: 0, name: "person" }] }],
  tracker_configs: [{ tracker_config_id: "bytetrack-default" }],
};

const video = {
  video_id: "video-1",
  filename: "clip.mp4",
  width: 160,
  height: 96,
  fps: 10,
  duration_s: 0.4,
  frame_count: 4,
  preview_ready: false,
  created_at: "2026-10-16T00:00:00Z",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const path = new URL(String(url)).pathname;
      if (path === "/api/models") return Response.json(catalog);
      if (path === "/api/processing-defaults") return Response.json(defaults);
      if (path === "/api/videos" && init?.method === "POST")
        return Response.json(video, { status: 201 });
      if (path === "/api/jobs" && init?.method === "POST") {
        return Response.json(
          {
            error_code: "invalid_job",
            error: "Detector confidence must be <= tracker low threshold",
          },
          { status: 422 },
        );
      }
      return new Response("missing", { status: 404 });
    }),
  );
});

it("keeps the line when the server rejects the job", async () => {
  const user = userEvent.setup();
  render(
    <Suspense fallback={null}>
      <Workspace />
    </Suspense>,
  );
  expect(await screen.findByRole("checkbox", { name: "person" })).toBeVisible();
  const file = new File(["frame"], "clip.mp4", { type: "video/mp4" });
  await user.upload(screen.getByLabelText("Video file"), file);
  await user.click(screen.getByRole("button", { name: "Upload" }));
  expect(await screen.findByRole("status")).toHaveTextContent(
    "Uploaded clip.mp4.",
  );
  await user.clear(screen.getByLabelText("End time (s)"));
  await user.type(screen.getByLabelText("End time (s)"), "0");
  await user.click(screen.getByRole("button", { name: "Add line" }));
  await user.click(screen.getByRole("button", { name: "Start job" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/End time/);
  expect(screen.getByLabelText("Line ID 1")).toHaveValue("line-1");

  await user.clear(screen.getByLabelText("End time (s)"));
  await user.click(screen.getByRole("button", { name: "Start job" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    /tracker low threshold/,
  );
  expect(screen.getByLabelText("Line ID 1")).toHaveValue("line-1");
});
