import type { HealthResponse } from "@/types/api";

export function getApiBaseUrl(): string {
  const url = new URL(
    process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
  );
  if (
    !["http:", "https:"].includes(url.protocol) ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/"
  ) {
    throw new Error("NEXT_PUBLIC_API_URL must be an HTTP(S) origin");
  }
  return url.origin;
}

export async function fetchHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const timeout = AbortSignal.timeout(5_000);
  const response = await fetch(`${getApiBaseUrl()}/api/health`, {
    cache: "no-store",
    signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
  });
  if (!response.ok) {
    throw new Error(`Health request failed (${response.status})`);
  }
  const data: unknown = await response.json();
  if (
    typeof data !== "object" ||
    data === null ||
    !("status" in data) ||
    data.status !== "ok" ||
    !("service" in data) ||
    data.service !== "intelligent-traffic-tracking-api" ||
    !("api_version" in data) ||
    data.api_version !== "v1"
  ) {
    throw new Error("Unexpected health response");
  }
  return {
    status: data.status,
    service: data.service,
    api_version: data.api_version,
  };
}
