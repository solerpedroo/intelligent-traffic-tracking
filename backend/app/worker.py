"""One active job per process. The API never calls this during a request."""

from backend.app.repository import (
    cancel_requested,
    claim_next,
    finish,
    now,
    open_db,
    recover_stale,
    touch,
)
from backend.app.storage import job_dir
from vision.contracts import ProcessingConfig
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
            )
        else:
            summary = processor(video, output, config, progress, should_cancel)
        if cancel_requested(connection, job_id):
            finish(connection, job_id, "cancelled", now(), "cancelled", "Cancellation requested")
            return
        status = summary.get("status", "completed") if isinstance(summary, dict) else "completed"
        finish(connection, job_id, "completed", now(), summary_status=status)
    except VideoError as error:
        state = "cancelled" if error.code == "cancelled" else "failed"
        finish(connection, job_id, state, now(), error.code, str(error))
    except OSError as error:
        finish(connection, job_id, "failed", now(), "disk_error", str(error))
    finally:
        connection.close()


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


def main() -> None:
    from backend.app.core.config import Settings

    settings = Settings()
    while True:
        run_available(settings, max_jobs=1)


if __name__ == "__main__":
    main()
