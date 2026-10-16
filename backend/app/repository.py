"""Transactional job queue. An interrupted run is failed, not resumed."""

import json
import sqlite3
from datetime import UTC, datetime, timedelta

from backend.app.db import connect, database_path
from backend.app.storage import job_dir, remove_tree


def now() -> datetime:
    return datetime.now(UTC)


def iso(moment: datetime) -> str:
    return moment.isoformat()


def open_db(settings):
    return connect(database_path(settings.data_dir))


def insert_video(connection, video: dict) -> None:
    connection.execute(
        """
        INSERT INTO videos (
          id, filename, sha256, size_bytes, width, height, fps, duration_s,
          frame_count, created_at, preview_ready
        ) VALUES (:id, :filename, :sha256, :size_bytes, :width, :height, :fps,
          :duration_s, :frame_count, :created_at, :preview_ready)
        """,
        video,
    )


def get_video(connection, video_id: str):
    return connection.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()


def insert_job(connection, job: dict) -> None:
    connection.execute(
        """
        INSERT INTO jobs (
          id, video_id, state, stage, processed_frames, total_frames, config_json, created_at
        ) VALUES (:id, :video_id, 'queued', 'queued', 0, :total_frames, :config_json, :created_at)
        """,
        job,
    )


def get_job(connection, job_id: str):
    return connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def list_jobs(connection, *, state: str | None, limit: int, offset: int):
    if state is None:
        rows = connection.execute(
            "SELECT * FROM jobs ORDER BY created_at, id LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    else:
        rows = connection.execute(
            "SELECT * FROM jobs WHERE state=? ORDER BY created_at, id LIMIT ? OFFSET ?",
            (state, limit, offset),
        ).fetchall()
        count = connection.execute("SELECT COUNT(*) FROM jobs WHERE state=?", (state,))
        total = count.fetchone()[0]
    return rows, total


def request_cancel(connection, job_id: str, moment: datetime) -> str | None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = get_job(connection, job_id)
        if row is None:
            connection.execute("COMMIT")
            return None
        if row["state"] == "queued":
            connection.execute(
                """
                UPDATE jobs
                SET state='cancelled', stage='cancelled', cancel_requested=1, finished_at=?
                WHERE id=? AND state='queued'
                """,
                (iso(moment), job_id),
            )
        elif row["state"] == "running":
            connection.execute(
                "UPDATE jobs SET cancel_requested=1 WHERE id=? AND state='running'",
                (job_id,),
            )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return get_job(connection, job_id)["state"]


def claim_next(connection, moment: datetime):
    connection.execute("BEGIN IMMEDIATE")
    try:
        row = connection.execute(
            """
            SELECT id FROM jobs
            WHERE state='queued' AND cancel_requested=0
            ORDER BY created_at, id LIMIT 1
            """
        ).fetchone()
        if row is None:
            connection.execute("COMMIT")
            return None
        stamp = iso(moment)
        updated = connection.execute(
            """
            UPDATE jobs
            SET state='running', stage='running', started_at=?, heartbeat_at=?, attempt=attempt+1
            WHERE id=? AND state='queued'
            """,
            (stamp, stamp, row["id"]),
        )
        if updated.rowcount != 1:
            connection.execute("ROLLBACK")
            return None
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise
    return get_job(connection, row["id"])


def touch(connection, job_id: str, moment: datetime, processed: int, stage: str) -> None:
    connection.execute(
        """
        UPDATE jobs
        SET heartbeat_at=?, processed_frames=?, stage=?
        WHERE id=? AND state='running'
        """,
        (iso(moment), processed, stage, job_id),
    )


def cancel_requested(connection, job_id: str) -> bool:
    row = get_job(connection, job_id)
    return bool(row and row["cancel_requested"])


def finish(
    connection,
    job_id: str,
    state: str,
    moment: datetime,
    error_code=None,
    error=None,
    summary_status=None,
    processed_frames=None,
):
    connection.execute(
        """
        UPDATE jobs
        SET state=?, stage=?, finished_at=?, heartbeat_at=?, error_code=?, error=?,
            summary_status=?,
            processed_frames=COALESCE(?, processed_frames)
        WHERE id=? AND state='running'
        """,
        (
            state,
            state,
            iso(moment),
            iso(moment),
            error_code,
            error,
            summary_status,
            processed_frames,
            job_id,
        ),
    )


def recover_stale(connection, moment: datetime, stale_after_seconds: int) -> int:
    cutoff = iso(moment - timedelta(seconds=stale_after_seconds))
    updated = connection.execute(
        """
        UPDATE jobs
        SET state='failed', stage='failed', finished_at=?, error_code='worker_interrupted',
            error='Worker stopped before publishing results'
        WHERE state='running' AND (heartbeat_at IS NULL OR heartbeat_at < ?)
        """,
        (iso(moment), cutoff),
    )
    return updated.rowcount


def cleanup_expired(settings, moment: datetime) -> int:
    connection = open_db(settings)
    try:
        cutoff = iso(moment - timedelta(seconds=settings.retention_seconds))
        rows = connection.execute(
            """
            SELECT id FROM jobs
            WHERE state IN ('completed', 'failed', 'cancelled') AND finished_at < ?
            """,
            (cutoff,),
        ).fetchall()
        for row in rows:
            remove_tree(job_dir(settings.data_dir, row["id"]))
            connection.execute("DELETE FROM jobs WHERE id=?", (row["id"],))
        return len(rows)
    finally:
        connection.close()


def public_job(row: sqlite3.Row) -> dict:
    return {
        "job_id": row["id"],
        "video_id": row["video_id"],
        "state": row["state"],
        "stage": row["stage"],
        "processed_frames": row["processed_frames"],
        "total_frames": row["total_frames"],
        "error_code": row["error_code"],
        "error": row["error"],
        "summary_status": row["summary_status"],
        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "cancel_requested": bool(row["cancel_requested"]),
        "attempt": row["attempt"],
        "config": json.loads(row["config_json"]),
    }
