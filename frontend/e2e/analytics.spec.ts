import { expect, type Route, test } from "@playwright/test";

const job = {
  job_id: "job-1",
  video_id: "video-1",
  state: "completed",
  stage: "completed",
  processed_frames: 4,
  total_frames: 4,
  error_code: null,
  error: null,
  summary_status: "completed",
  created_at: "2026-10-16T00:00:00Z",
  cancel_requested: false,
  config: { render_annotated_video: false, counting: { lines: [] } },
};

test("reads counts from artifacts and refuses an incompatible comparison", async ({
  page,
}) => {
  await page.route("**/api/**", async (route: Route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/api/jobs") {
      await route.fulfill({
        json: {
          items: [job, { ...job, job_id: "job-2", video_id: "video-2" }],
          total: 2,
          limit: 20,
          offset: 0,
        },
      });
      return;
    }
    if (path === "/api/models") {
      await route.fulfill({
        json: {
          models: [
            { model_id: "yolo11n-coco", classes: [{ id: 2, name: "car" }] },
          ],
          tracker_configs: [],
        },
      });
      return;
    }
    if (path === "/api/jobs/job-1") {
      await route.fulfill({ json: job });
      return;
    }
    if (path.endsWith("/summary.json")) {
      await route.fulfill({
        json: {
          counting: {
            total_events: 2,
            by_line_direction: [
              { line_id: "gate", direction: "A_TO_B", count: 2 },
            ],
            by_line_class_direction: [],
          },
          tracker: { mot_evaluation: "not_evaluated_no_ground_truth" },
          inference_fps: null,
          elapsed_s: 1,
          end_to_end_fps: 4,
        },
      });
      return;
    }
    if (path.endsWith("/config.json")) {
      const video = path.includes("job-2") ? "video-2" : "video-1";
      await route.fulfill({
        json: {
          video_id: video,
          start_s: 0,
          end_s: null,
          detector_model_id: "yolo11n-coco",
        },
      });
      return;
    }
    if (path.endsWith("/manifest.json")) {
      await route.fulfill({
        json: { hardware: "cpu", detector: { checkpoint_sha256: "abc" } },
      });
      return;
    }
    await route.fulfill({ status: 404, body: "" });
  });

  await page.goto("/analytics?job=job-1");
  await expect(page.getByText("2 events in summary.json")).toBeVisible();
  await expect(
    page.getByText(/Confirmed ID switches need ground truth/),
  ).toBeVisible();
  await page.getByRole("link", { name: "Compare" }).click();
  await page.getByLabel("Left job").selectOption("job-1");
  await page.getByLabel("Right job").selectOption("job-2");
  await expect(page.getByText(/not a controlled ablation/)).toBeVisible();
  await expect(page.getByText("Different videos")).toBeVisible();
});
