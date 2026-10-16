"""One active job per process. The API never calls this during a request."""

import time

from backend.app.repository import (
    cancel_requested,
    claim_next,
    cleanup_expired,
    finish,
    now,
    open_db,
    recover_stale,
    touch,
)
from backend.app.storage import job_dir
from vision.contracts import ProcessingConfig
from vision.contracts.errors import VisionError
from vision.video.errors import VideoError


def execute(settings, job, *, processor=None) -> None:
    connection = open_db(settings)
    job_id = job["id"]

    def should_cancel():
        if cancel_requested(connection, job_id):
            raise VideoError("cancelled", "Cancellation requested")

    def progress(processed, total, stage):
        touch(connection, job_id, now(), processed, stage)

    try:
        should_cancel()
        output = job_dir(settings.data_dir, job_id)
        config = ProcessingConfig.model_validate_json(job["config_json"])
        video = settings.data_dir / "videos" / job["video_id"] / "source.mp4"
        if processor is None:
            from vision.pipeline.video import process_video

            summary = process_video(
                video,
                output,
                config=config,
                cancel_check=should_cancel,
                checkpoint=resolve_checkpoint(settings, config),
                progress=lambda count: progress(count, job["total_frames"], "processing"),
            )
        else:
            summary = processor(video, output, config, progress, should_cancel)
        if cancel_requested(connection, job_id):
            finish(connection, job_id, "cancelled", now(), "cancelled", "Cancellation requested")
            return
        status = "completed"
        frames = None
        if isinstance(summary, dict):
            status = summary.get("status", "completed")
            frames = summary.get("selected_frames")
        finish(
            connection,
            job_id,
            "completed",
            now(),
            summary_status=status,
            processed_frames=frames,
        )
    except VisionError as error:
        state = "cancelled" if error.code == "cancelled" else "failed"
        finish(connection, job_id, state, now(), error.code, str(error))
    except OSError as error:
        finish(connection, job_id, "failed", now(), "disk_error", str(error))
    except Exception as error:
        finish(connection, job_id, "failed", now(), "worker_error", str(error))
    finally:
        connection.close()


def resolve_checkpoint(settings, config: ProcessingConfig):
    if config.detector_model_id is None:
        return None
    from vision.configs import load_catalog
    from vision.detectors.checkpoint import verify_checkpoint

    model = load_catalog().get_model(config.detector_model_id)
    return verify_checkpoint(settings.checkpoint_dir / model.filename, model)


def run_available(settings, *, processor=None, max_jobs: int = 1) -> int:
    connection = open_db(settings)
    try:
        recover_stale(connection, now(), settings.stale_after_seconds)
        claimed = 0
        while claimed < max_jobs:
            job = claim_next(connection, now())
            if job is None:
                break
            claimed += 1
            connection.close()
            execute(settings, job, processor=processor)
            connection = open_db(settings)
        return claimed
    finally:
        connection.close()


def recover(settings) -> int:
    connection = open_db(settings)
    try:
        return recover_stale(connection, now(), settings.stale_after_seconds)
    finally:
        connection.close()


def cycle(settings, *, processor=None, max_jobs: int = 1) -> int:
    """Recover stale jobs, run queued work, then delete expired results."""
    try:
        claimed = run_available(settings, processor=processor, max_jobs=max_jobs)
    finally:
        cleanup_expired(settings, now())
    return claimed


def main() -> None:
    from backend.app.core.config import Settings

    settings = Settings()
    while True:
        try:
            claimed = cycle(settings)
        except Exception:
            claimed = 0
        if claimed == 0:
            time.sleep(0.5)


if __name__ == "__main__":
    main()
