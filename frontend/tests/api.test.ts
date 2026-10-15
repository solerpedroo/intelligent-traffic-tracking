import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchHealth, getApiBaseUrl } from "@/lib/api";

const health = {
  status: "ok",
  service: "intelligent-traffic-tracking-api",
  api_version: "v1",
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("API boundary", () => {
  it("normalizes an explicitly configured origin", () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000/");
    expect(getApiBaseUrl()).toBe("http://localhost:8000");
  });

  it.each([
    "file:///tmp/api",
    "https://example.com/api",
    "https://user:secret@example.com",
    "https://example.com/?token=x",
  ])("rejects a non-origin URL: %s", (url) => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", url);
    expect(() => getApiBaseUrl()).toThrow();
  });

  it("validates the health response at runtime", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    const fetchMock = vi.fn().mockResolvedValue(Response.json(health));
    vi.stubGlobal("fetch", fetchMock);
    await expect(fetchHealth()).resolves.toEqual(health);
    expect(fetchMock).toHaveBeenCalledWith("http://localhost:8000/api/health", {
      cache: "no-store",
      signal: expect.any(AbortSignal),
    });
  });

  it("does not treat an invalid successful payload as healthy", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(Response.json({ status: "ok" })),
    );
    await expect(fetchHealth()).rejects.toThrow("Unexpected health response");
  });

  it("reports HTTP failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 503 })),
    );
    await expect(fetchHealth()).rejects.toThrow("503");
  });
});
