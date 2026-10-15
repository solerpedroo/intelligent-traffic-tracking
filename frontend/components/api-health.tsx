"use client";

import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";

export function ApiHealth() {
  const [state, setState] = useState<"checking" | "available" | "unavailable">(
    "checking",
  );

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then(() => setState("available"))
      .catch(() => {
        if (!controller.signal.aborted) setState("unavailable");
      });
    return () => controller.abort();
  }, []);

  const messages = {
    checking: "Checking API…",
    available: "API available",
    unavailable: "API unavailable — check the local server and API URL.",
  };

  return (
    <div className="health" role="status" aria-live="polite">
      <span className={`status-dot ${state}`} aria-hidden="true" />
      {messages[state]}
    </div>
  );
}
