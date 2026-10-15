/** Liveness only: does not imply detector, data, or worker readiness. */
export type HealthResponse = {
  status: "ok";
  service: "intelligent-traffic-tracking-api";
  api_version: "v1";
};
