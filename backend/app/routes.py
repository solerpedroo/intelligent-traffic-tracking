"""HTTP translation only. Inference stays in the worker process."""

import hashlib
import json
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from backend.app.repository import (
    get_job,
    get_video,
    insert_job,
    insert_video,
    iso,
    list_jobs,
    now,
    open_db,
    public_job,
    request_cancel,
)
from backend.app.storage import (
    artifact_path,
    directory_size,
    job_dir,
    video_dir,
)

router = APIRouter()


def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "error": message})


def install(app, settings) -> None:
    app.state.settings = settings

    @app.exception_handler(HTTPException)
    def render_error(_request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            detail = exc.detail
        else:
            detail = {"error_code": "http_error", "error": str(exc.detail)}
        return JSONResponse(detail, status_code=exc.status_code)

    app.include_router(router)


@router.post("/api/videos", status_code=201)
async def upload_video(request: Request):
    settings = request.app.state.settings
    if directory_size(settings.data_dir) >= settings.quota_bytes:
        raise error(413, "quota_exceeded", "Storage quota is full")
    payload = await request.body()
    if len(payload) > settings.max_upload_bytes:
        raise error(413, "upload_too_large", "Video exceeds the upload limit")
    if not payload:
        raise error(422, "invalid_video", "Video file is empty")
    video_id = uuid4().hex
    directory = video_dir(settings.data_dir, video_id)
    directory.mkdir(parents=True, exist_ok=False)
    source = directory / "source.mp4"
    source.write_bytes(payload)
    try:
        from vision.video import probe_video

        metadata = probe_video(source)
    except Exception as exc:
        source.unlink(missing_ok=True)
        directory.rmdir()
        raise error(422, "invalid_video", "Video could not be probed") from exc
    preview_ready = 0
    try:
        import cv2

        from vision.video import VideoReader

        with VideoReader(source) as reader:
            frame = next(iter(reader))
        ok, encoded = cv2.imencode(".png", frame.pixels)
        if ok:
            (directory / "preview.png").write_bytes(encoded.tobytes())
            preview_ready = 1
    except Exception:
        preview_ready = 0
    record = {
        "id": video_id,
        "filename": request.headers.get("x-filename", "video.mp4").rsplit("/", 1)[-1],
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
        "width": metadata.width,
        "height": metadata.height,
        "fps": metadata.reported_fps,
        "duration_s": metadata.reported_duration_s,
        "frame_count": metadata.reported_frames,
        "created_at": iso(now()),
        "preview_ready": preview_ready,
    }
    connection = open_db(settings)
    try:
        insert_video(connection, record)
    finally:
        connection.close()
    return video_payload(record)


@router.get("/api/videos/{video_id}")
def read_video(video_id: str, request: Request):
    connection = open_db(request.app.state.settings)
    try:
        row = get_video(connection, video_id)
    finally:
        connection.close()
    if row is None:
        raise error(404, "video_not_found", "Video was not found")
    return video_payload(row)


@router.get("/api/models")
def read_models():
    from vision.configs import load_catalog

    catalog = load_catalog()
    return catalog.model_dump(mode="json")


@router.get("/api/videos/{video_id}/preview")
def read_preview(video_id: str, request: Request):
    settings = request.app.state.settings
    connection = open_db(settings)
    try:
        row = get_video(connection, video_id)
    finally:
        connection.close()
    if row is None:
        raise error(404, "video_not_found", "Video was not found")
    path = video_dir(settings.data_dir, video_id) / "preview.png"
    if not row["preview_ready"] or not path.is_file():
        raise error(404, "preview_unavailable", "Preview frame is not available")
    return FileResponse(path, media_type="image/png", filename="preview.png")


@router.get("/api/processing-defaults")
def processing_defaults():
    from vision.contracts import ProcessingConfig

    payload = ProcessingConfig(video_id="example").model_dump(mode="json")
    payload.pop("video_id", None)
    payload.pop("schema_version", None)
    return payload


@router.post("/api/jobs", status_code=202)
async def create_job(request: Request):
    settings = request.app.state.settings
    try:
        raw = await request.json()
    except Exception as exc:
        raise error(422, "invalid_job", "Job body must be a JSON object") from exc
    if not isinstance(raw, dict) or not isinstance(raw.get("video_id"), str):
        raise error(422, "invalid_job", "video_id is required")
    raw.setdefault("render_annotated_video", False)
    video_id = raw["video_id"]
    connection = open_db(settings)
    try:
        video = get_video(connection, video_id)
        if video is None:
            raise error(404, "video_not_found", "Video was not found")
        from vision.contracts import ProcessingConfig

        try:
            config = ProcessingConfig.model_validate_json(json.dumps(raw))
        except ValidationError as exc:
            first = exc.errors()[0]["msg"] if exc.errors() else "Job configuration is invalid"
            message = first
            raise error(422, "invalid_job", message) from exc
        job_id = uuid4().hex
        insert_job(
            connection,
            {
                "id": job_id,
                "video_id": video_id,
                "total_frames": video["frame_count"],
                "config_json": config.model_dump_json(),
                "created_at": iso(now()),
            },
        )
        row = get_job(connection, job_id)
    finally:
        connection.close()
    return public_job(row)


@router.get("/api/jobs")
def read_jobs(
    request: Request,
    state: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    connection = open_db(request.app.state.settings)
    try:
        rows, total = list_jobs(connection, state=state, limit=limit, offset=offset)
    finally:
        connection.close()
    return {
        "items": [public_job(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/jobs/{job_id}")
def read_job(job_id: str, request: Request):
    row = _job_or_404(request, job_id)
    return public_job(row)


@router.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request):
    connection = open_db(request.app.state.settings)
    try:
        state = request_cancel(connection, job_id, now())
        row = get_job(connection, job_id)
    finally:
        connection.close()
    if state is None:
        raise error(404, "job_not_found", "Job was not found")
    return public_job(row)


@router.get("/api/jobs/{job_id}/summary")
def read_summary(job_id: str, request: Request):
    row = _job_or_404(request, job_id)
    if row["state"] != "completed":
        raise error(409, "job_not_completed", "Summary is published only after completion")
    path = artifact_path(job_dir(request.app.state.settings.data_dir, job_id), "summary.json")
    if path is None:
        raise error(404, "artifact_missing", "Summary file is missing")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/api/jobs/{job_id}/events")
def read_events(
    job_id: str,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    _job_or_404(request, job_id)
    return _page_csv(request, job_id, "crossing_events.csv", limit, offset)


@router.get("/api/jobs/{job_id}/tracks")
def read_tracks(
    job_id: str,
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    _job_or_404(request, job_id)
    return _page_csv(request, job_id, "tracks.csv", limit, offset)


@router.get("/api/jobs/{job_id}/artifacts/{name}")
def download_artifact(job_id: str, name: str, request: Request):
    _job_or_404(request, job_id)
    path = artifact_path(job_dir(request.app.state.settings.data_dir, job_id), name)
    if path is None:
        raise error(404, "artifact_not_allowed", "Artifact name is not available")
    return FileResponse(path, filename=name)


@router.get("/api/experiments")
def read_experiments(request: Request):
    connection = open_db(request.app.state.settings)
    try:
        rows, _total = list_jobs(connection, state="completed", limit=100, offset=0)
    finally:
        connection.close()
    return {
        "items": [
            {
                "job_id": row["id"],
                "video_id": row["video_id"],
                "summary_status": row["summary_status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


def _job_or_404(request: Request, job_id: str):
    connection = open_db(request.app.state.settings)
    try:
        row = get_job(connection, job_id)
    finally:
        connection.close()
    if row is None:
        raise error(404, "job_not_found", "Job was not found")
    return row


def _page_csv(request: Request, job_id: str, name: str, limit: int, offset: int):
    import csv

    path = artifact_path(job_dir(request.app.state.settings.data_dir, job_id), name)
    if path is None:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        "items": rows[offset : offset + limit],
        "total": len(rows),
        "limit": limit,
        "offset": offset,
    }


def video_payload(row) -> dict:
    data = dict(row) if not isinstance(row, dict) else row
    return {
        "video_id": data["id"],
        "filename": data["filename"],
        "sha256": data["sha256"],
        "size_bytes": data["size_bytes"],
        "width": data["width"],
        "height": data["height"],
        "fps": data["fps"],
        "duration_s": data["duration_s"],
        "frame_count": data["frame_count"],
        "preview_ready": bool(data["preview_ready"]),
        "created_at": data["created_at"],
    }
