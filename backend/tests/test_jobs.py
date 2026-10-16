"""Job lifecycle against SQLite. Inference is not executed inside the request."""

import threading
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.repository import claim_next, get_job, iso, now, open_db
from backend.app.storage import job_dir
from backend.app.worker import recover, run_available
from scripts.generate_sample import generate_sample
from vision.video.errors import VideoError


def settings(tmp_path, **overrides):
    return Settings(data_dir=tmp_path, **overrides)


def client_for(cfg):
    return TestClient(create_app(cfg))


def upload(client, tmp_path):
    video = tmp_path / "sample.mp4"
    generate_sample(video, frames=4, width=160, height=96)
    payload = video.read_bytes()
    response = client.post(
        "/api/videos",
        content=payload,
        headers={"content-type": "application/octet-stream", "x-filename": "sample.mp4"},
    )
    assert response.status_code == 201, response.text
    return response.json()["video_id"]


def test_invalid_upload_is_rejected(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        response = client.post(
            "/api/videos",
            content=b"not-a-video",
            headers={"content-type": "application/octet-stream", "x-filename": "bad.mp4"},
        )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_video"


def test_http_cycle_does_not_infer_inside_the_request(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        created = client.post("/api/jobs", json={"video_id": video_id})
        assert created.status_code == 202
        body = created.json()
        assert body["state"] == "queued"
        assert client.get("/api/models").status_code == 200
        queued = client.get(f"/api/jobs/{body['job_id']}")
        assert queued.json()["state"] == "queued"
    assert run_available(cfg) == 1
    with client_for(cfg) as restarted:
        job = restarted.get(f"/api/jobs/{body['job_id']}").json()
        assert job["state"] == "completed"
        summary = restarted.get(f"/api/jobs/{body['job_id']}/summary")
        assert summary.status_code == 200
        assert summary.json()["selected_frames"] == 4
        download = restarted.get(f"/api/jobs/{body['job_id']}/artifacts/summary.json")
        assert download.status_code == 200
        escaped = restarted.get(f"/api/jobs/{body['job_id']}/artifacts/not-allowed.txt")
        assert escaped.status_code == 404
        from backend.app.storage import artifact_path

        assert artifact_path(job_dir(tmp_path, body["job_id"]), "../secret") is None
        again = restarted.post("/api/jobs", json={"video_id": video_id})
        assert again.json()["job_id"] != body["job_id"]
        assert (job_dir(tmp_path, body["job_id"]) / "summary.json").is_file()


def test_only_one_worker_claims_a_job(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        client.post("/api/jobs", json={"video_id": video_id})
    barrier = threading.Barrier(2)
    found = []

    def claim():
        connection = open_db(cfg)
        barrier.wait()
        job = claim_next(connection, now())
        found.append(job["id"] if job else None)
        connection.close()

    threads = [threading.Thread(target=claim) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert found.count(None) == 1


def test_stale_worker_becomes_failed_and_reprocess_is_a_new_job(tmp_path):
    cfg = settings(tmp_path, stale_after_seconds=1)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
    connection = open_db(cfg)
    claim_next(connection, now())
    connection.execute(
        "UPDATE jobs SET heartbeat_at=? WHERE id=?",
        ("2000-01-01T00:00:00+00:00", job_id),
    )
    connection.close()
    assert recover(cfg) == 1
    with client_for(cfg) as client:
        assert client.get(f"/api/jobs/{job_id}").json()["error_code"] == "worker_interrupted"
        replacement = client.post("/api/jobs", json={"video_id": video_id}).json()
    assert replacement["job_id"] != job_id
    assert replacement["state"] == "queued"


def test_cancel_queued_and_running(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        queued = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
        assert client.post(f"/api/jobs/{queued}/cancel").json()["state"] == "cancelled"
        running = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]

    def processor(video, output, config, progress, should_cancel):
        progress(0, 1, "running")
        with client_for(cfg) as client:
            client.post(f"/api/jobs/{running}/cancel")
        should_cancel()
        return {"status": "completed"}

    assert run_available(cfg, processor=processor) == 1
    connection = open_db(cfg)
    assert get_job(connection, running)["state"] == "cancelled"
    connection.close()


def test_disk_error_is_not_completion(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]

    def processor(*_args):
        raise OSError(28, "No space left on device")

    run_available(cfg, processor=processor)
    with client_for(cfg) as client:
        body = client.get(f"/api/jobs/{job_id}").json()
        assert body["state"] == "failed"
        assert body["error_code"] == "disk_error"
        assert client.get(f"/api/jobs/{job_id}/summary").status_code == 409


def test_cleanup_keeps_the_active_job(tmp_path):
    cfg = settings(tmp_path, retention_seconds=0)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        old = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
        active = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
    run_available(cfg, max_jobs=1)
    connection = open_db(cfg)
    past = iso(datetime.now(UTC) - timedelta(days=1))
    connection.execute("UPDATE jobs SET finished_at=? WHERE id=?", (past, old))
    claim_next(connection, now())
    connection.close()
    from backend.app.repository import cleanup_expired

    assert cleanup_expired(cfg, now()) == 1
    connection = open_db(cfg)
    assert get_job(connection, old) is None
    assert get_job(connection, active)["state"] == "running"
    connection.close()


def test_running_cancellation_uses_the_pipeline_checkpoint(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
    connection = open_db(cfg)
    claim_next(connection, now())
    connection.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (job_id,))
    connection.close()

    def checker():
        raise VideoError("cancelled", "Cancellation requested")

    from vision.contracts import ProcessingConfig
    from vision.pipeline.video import process_video

    video = tmp_path / "direct.mp4"
    generate_sample(video, frames=2, width=160, height=96)
    try:
        process_video(
            video,
            tmp_path / "out",
            config=ProcessingConfig(video_id="clip", render_annotated_video=False),
            cancel_check=checker,
        )
    except VideoError as error:
        assert error.code == "cancelled"
    else:
        raise AssertionError("cancel check was not honored")
