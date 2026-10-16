import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchHealth, fetchTable, getApiBaseUrl } from "@/lib/api";

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

  it("pages table rows until the cap and keeps the file total", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    const fetchMock = vi.fn(async (url: string) => {
      const parsed = new URL(url);
      const offset = Number(parsed.searchParams.get("offset"));
      const limit = Number(parsed.searchParams.get("limit"));
      const items = Array.from({ length: limit }, (_, index) => ({
        track_id: String(offset + index),
      }));
      return Response.json({ items, total: 2500, limit, offset });
    });
    vi.stubGlobal("fetch", fetchMock);
    const page = await fetchTable("job-1", "events");
    expect(page.items).toHaveLength(1000);
    expect(page.total).toBe(2500);
    expect(fetchMock).toHaveBeenCalledTimes(10);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain("offset=100");
  });

  it("stops table paging when a page is short", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const offset = Number(new URL(url).searchParams.get("offset"));
        const items =
          offset === 0
            ? Array.from({ length: 100 }, (_, index) => ({
                track_id: String(index),
              }))
            : [{ track_id: "100" }];
        return Response.json({
          items,
          total: 101,
          limit: items.length,
          offset,
        });
      }),
    );
    const page = await fetchTable("job-1", "tracks");
    expect(page.items).toHaveLength(101);
    expect(page.total).toBe(101);
  });

  it("reports HTTP failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 503 })),
    );
    await expect(fetchHealth()).rejects.toThrow("503");
  });
});
