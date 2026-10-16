import { Suspense } from "react";
import { Workspace } from "@/components/workspace";

export default function WorkspacePage() {
  return (
    <Suspense
      fallback={
        <main>
          <p role="status">Loading workspace…</p>
        </main>
      }
    >
      <Workspace />
    </Suspense>
  );
}
