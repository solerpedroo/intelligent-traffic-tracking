import { expect, type Route, test } from "@playwright/test";

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

const job = {
  job_id: "job-1",
  video_id: "video-1",
  stage: null,
  processed_frames: 0,
  total_frames: 4,
  error_code: null,
  error: null,
  summary_status: null,
  created_at: "2026-10-16T00:00:00Z",
  cancel_requested: false,
  config: {
    render_annotated_video: false,
    counting: { lines: [{ line_id: "line-1" }] },
  },
};

test("uploads a line, queues a job, and opens its exports", async ({
  page,
}) => {
  let jobReads = 0;
  await page.route("**/api/**", async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    if (path === "/api/health") {
      await route.fulfill({
        json: {
          status: "ok",
          service: "intelligent-traffic-tracking-api",
          api_version: "v1",
        },
      });
      return;
    }
    if (path === "/api/jobs" && method === "GET") {
      await route.fulfill({
        json: { items: [], total: 0, limit: 20, offset: 0 },
      });
      return;
    }
    if (path === "/api/models") {
      await route.fulfill({ json: catalog });
      return;
    }
    if (path === "/api/processing-defaults") {
      await route.fulfill({ json: defaults });
      return;
    }
    if (path === "/api/videos" && method === "POST") {
      await route.fulfill({ status: 201, json: video });
      return;
    }
    if (path === "/api/jobs" && method === "POST") {
      const body = route.request().postDataJSON() as {
        counting: { lines: { line_id: string }[] };
      };
      expect(body.counting.lines[0]?.line_id).toBe("line-1");
      await route.fulfill({ status: 202, json: { ...job, state: "queued" } });
      return;
    }
    if (path === "/api/jobs/job-1" && method === "GET") {
      jobReads += 1;
      const completed = jobReads > 1;
      await route.fulfill({
        json: {
          ...job,
          state: completed ? "completed" : "queued",
          processed_frames: completed ? 4 : 0,
          summary_status: completed ? "completed" : null,
        },
      });
      return;
    }
    if (path === "/api/videos/video-1") {
      await route.fulfill({ json: video });
      return;
    }
    if (path.endsWith("/events") || path.endsWith("/tracks")) {
      await route.fulfill({
        json: {
          items: [
            {
              line_id: "line-1",
              track_id: "3",
              class_id: "2",
              direction: "A_TO_B",
              timestamp_s: "0.2",
              frame_index: "1",
              state: "confirmed",
            },
          ],
          total: 1,
          limit: 100,
          offset: 0,
        },
      });
      return;
    }
    await route.fulfill({
      status: 404,
      json: { error_code: "missing", error: path },
    });
  });

  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Understand movement/ }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Open workspace" }).click();
  await page.getByLabel("Video file").setInputFiles({
    name: "clip.mp4",
    mimeType: "video/mp4",
    buffer: Buffer.from("frame"),
  });
  await page.getByRole("button", { name: "Upload" }).click();
  await expect(page.getByText("Uploaded clip.mp4.")).toBeVisible();
  await page.getByRole("button", { name: "Add line" }).click();
  await page.getByRole("button", { name: "Start job" }).click();
  await page.getByRole("link", { name: "Open this job in the viewer" }).click();
  await expect(page.getByRole("link", { name: "Summary JSON" })).toBeVisible();
  await expect(page.getByText("A_TO_B")).toBeVisible();
  await expect(
    page.getByText(/Annotated video was not requested/),
  ).toBeVisible();
});
