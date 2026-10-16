"use client";

import { useParams } from "next/navigation";
import { Viewer } from "@/components/viewer";

export default function JobViewerPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = Array.isArray(params.jobId) ? params.jobId[0] : params.jobId;
  if (!jobId)
    return (
      <main>
        <p role="alert">Job id is missing.</p>
      </main>
    );
  return <Viewer key={jobId} jobId={jobId} />;
}
