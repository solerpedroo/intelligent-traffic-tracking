import { describe, expect, it, vi } from "vitest";
import { pollUntilTerminal, shouldKeepPolling } from "@/lib/polling";

describe("job polling", () => {
  it("returns a terminal job without waiting", async () => {
    const wait = vi.fn();
    const job = await pollUntilTerminal(async () => ({ state: "completed" }), {
      wait,
      intervalMs: 2000,
      shouldContinue: () => true,
    });
    expect(job.state).toBe("completed");
    expect(wait).not.toHaveBeenCalled();
  });

  it("stops after the state becomes terminal", async () => {
    const states = ["queued", "running", "failed"];
    const wait = vi.fn(async () => undefined);
    const job = await pollUntilTerminal(
      async () => ({ state: states.shift() ?? "failed" }),
      { wait, intervalMs: 2000, shouldContinue: () => true },
    );
    expect(job.state).toBe("failed");
    expect(wait).toHaveBeenCalledTimes(2);
    expect(shouldKeepPolling(["completed", "cancelled"])).toBe(false);
    expect(shouldKeepPolling(["running"])).toBe(true);
  });

  it("stops when the caller unmounts during the interval", async () => {
    let active = true;
    const wait = vi.fn(async () => {
      active = false;
    });
    await expect(
      pollUntilTerminal(async () => ({ state: "queued" }), {
        wait,
        intervalMs: 2000,
        shouldContinue: () => active,
      }),
    ).rejects.toThrow(/stopped/);
  });
});
