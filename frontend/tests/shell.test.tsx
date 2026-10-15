import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import HomePage from "@/app/page";

afterEach(() => vi.unstubAllGlobals());

it("renders the foundation shell and confirms API liveness", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        status: "ok",
        service: "intelligent-traffic-tracking-api",
        api_version: "v1",
      }),
    ),
  );
  render(<HomePage />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
    "Understand movement",
  );
  expect(await screen.findByRole("status")).toBeInTheDocument();
  expect(await screen.findByText("API available")).toBeVisible();
});

it("keeps the shell usable when the API is offline", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
  );
  render(<HomePage />);
  expect(await screen.findByText(/API unavailable/)).toBeVisible();
  expect(screen.getByRole("heading", { level: 1 })).toBeVisible();
});
