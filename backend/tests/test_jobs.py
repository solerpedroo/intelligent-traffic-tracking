"""Job lifecycle against SQLite. Inference is not executed inside the request."""

import threading
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.repository import claim_next, get_job, get_video, iso, now, open_db
from backend.app.storage import job_dir, video_dir
from backend.app.worker import cycle, main, recover, run_available
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
    body = response.json()
    assert body["error_code"] == "unsupported_format"
    assert body["error"] == "Input must contain an ISO-BMFF ftyp header"


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
    assert get_video(connection, video_id) is not None
    connection.close()
    assert video_dir(tmp_path, video_id).is_dir()


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


def test_preview_and_normalized_geometry_are_stored_without_inference(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        preview = client.get(f"/api/videos/{video_id}/preview")
        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("image/png")
        defaults = client.get("/api/processing-defaults")
        assert defaults.status_code == 200
        assert "person" in defaults.json()["detector"]["classes"]
        created = client.post(
            "/api/jobs",
            json={
                "video_id": video_id,
                "detector_model_id": "yolo11n-coco",
                "tracker_config_id": "bytetrack-default",
                "counting": {
                    "lines": [
                        {"line_id": "gate", "start": [0, 0.5], "end": [1, 0.5]},
                    ]
                },
            },
        )
        assert created.status_code == 202, created.text
        assert created.json()["config"]["counting"]["lines"][0]["line_id"] == "gate"
        rejected = client.post(
            "/api/jobs",
            json={"video_id": video_id, "start_s": 2, "end_s": 1},
        )
        assert rejected.status_code == 422
        assert rejected.json()["error_code"] == "invalid_job"
        needs_tracker = client.post(
            "/api/jobs",
            json={
                "video_id": video_id,
                "counting": {
                    "lines": [
                        {"line_id": "gate", "start": [0, 0.5], "end": [1, 0.5]},
                    ]
                },
            },
        )
        assert needs_tracker.status_code == 422


def test_heatmap_preview_rejects_paths_outside_the_job(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
    heatmaps = job_dir(tmp_path, job_id) / "heatmaps"
    heatmaps.mkdir(parents=True)
    (heatmaps / "window.png").write_bytes(b"\x89PNG\r\n")
    with client_for(cfg) as client:
        preview = client.get(f"/api/jobs/{job_id}/heatmaps/window.png")
        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("image/png")
        assert client.get(f"/api/jobs/{job_id}/heatmaps/missing.png").status_code == 404
    from backend.app.storage import heatmap_preview_path

    assert heatmap_preview_path(job_dir(tmp_path, job_id), "../secret.png") is None


def test_parallel_connections_migrate_once(tmp_path):
    cfg = settings(tmp_path)
    errors = []

    def open_once():
        try:
            connection = open_db(cfg)
            connection.execute("SELECT COUNT(*) FROM videos").fetchone()
            connection.close()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=open_once) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []


def test_missing_checkpoint_fails_the_job(tmp_path):
    cfg = settings(tmp_path, checkpoint_dir=tmp_path / "absent")
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post(
            "/api/jobs",
            json={"video_id": video_id, "detector_model_id": "yolo11n-coco"},
        ).json()["job_id"]
    assert run_available(cfg) == 1
    with client_for(cfg) as client:
        body = client.get(f"/api/jobs/{job_id}").json()
    assert body["state"] == "failed"
    assert body["error_code"] == "missing_checkpoint"


def test_unexpected_processor_error_fails_the_job(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]

    def processor(*_args):
        raise RuntimeError("tracker exploded")

    assert run_available(cfg, processor=processor) == 1
    with client_for(cfg) as client:
        body = client.get(f"/api/jobs/{job_id}").json()
    assert body["state"] == "failed"
    assert body["error_code"] == "worker_error"


def test_content_length_above_upload_limit_is_rejected(tmp_path):
    cfg = settings(tmp_path, max_upload_bytes=8)
    with client_for(cfg) as client:
        response = client.post(
            "/api/videos",
            content=b"0123456789",
            headers={"content-type": "application/octet-stream", "x-filename": "big.mp4"},
        )
    assert response.status_code == 413
    assert response.json()["error_code"] == "upload_too_large"
    assert not (tmp_path / "videos").exists()


def test_quota_includes_the_incoming_upload(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        upload(client, tmp_path)
    from backend.app.storage import directory_size

    used = directory_size(tmp_path)
    payload = b"0123456789abcdef"
    tight = settings(tmp_path, quota_bytes=used + len(payload) - 1)
    assert used < tight.quota_bytes < used + len(payload)
    with client_for(tight) as client:
        response = client.post(
            "/api/videos",
            content=payload,
            headers={"content-type": "application/octet-stream", "x-filename": "more.mp4"},
        )
    assert response.status_code == 413
    assert response.json()["error_code"] == "quota_exceeded"


def test_probe_disk_error_is_not_invalid_video(tmp_path, monkeypatch):
    def boom(*_args, **_kwargs):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr("vision.video.probe_video", boom)
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        response = client.post(
            "/api/videos",
            content=b"not-a-video",
            headers={"content-type": "application/octet-stream", "x-filename": "bad.mp4"},
        )
    assert response.status_code == 507
    assert response.json()["error_code"] == "disk_error"
    videos = tmp_path / "videos"
    assert not videos.exists() or not any(videos.iterdir())


def test_probe_uses_configured_upload_limit(tmp_path, monkeypatch):
    from vision.video.models import VideoLimits
    from vision.video.reader import probe_video as real_probe

    captured = {}

    def spy(path, limits=None):
        captured["limits"] = limits
        return real_probe(path, limits)

    monkeypatch.setattr("vision.video.probe_video", spy)
    cfg = settings(tmp_path, max_upload_bytes=1024 * 1024)
    with client_for(cfg) as client:
        upload(client, tmp_path)
    limits = captured["limits"]
    defaults = VideoLimits()
    assert limits.max_bytes == cfg.max_upload_bytes
    assert limits.max_duration_s == defaults.max_duration_s
    assert limits.max_pixels == defaults.max_pixels
    assert limits.max_frames == defaults.max_frames


def test_jobs_are_listed_newest_first(tmp_path):
    cfg = settings(tmp_path)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        first = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
        second = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
    connection = open_db(cfg)
    connection.execute(
        "UPDATE jobs SET created_at=? WHERE id=?",
        ("2020-01-01T00:00:00+00:00", first),
    )
    connection.execute(
        "UPDATE jobs SET created_at=? WHERE id=?",
        ("2020-01-02T00:00:00+00:00", second),
    )
    connection.close()
    with client_for(cfg) as client:
        listed = client.get("/api/jobs").json()["items"]
        filtered = client.get("/api/jobs", params={"state": "queued"}).json()["items"]
    assert [item["job_id"] for item in listed] == [second, first]
    assert [item["job_id"] for item in filtered] == [second, first]


def test_cycle_deletes_an_old_completed_job(tmp_path):
    cfg = settings(tmp_path, retention_seconds=0)
    with client_for(cfg) as client:
        video_id = upload(client, tmp_path)
        job_id = client.post("/api/jobs", json={"video_id": video_id}).json()["job_id"]
    assert run_available(cfg) == 1
    connection = open_db(cfg)
    past = iso(datetime.now(UTC) - timedelta(days=1))
    connection.execute("UPDATE jobs SET finished_at=? WHERE id=?", (past, job_id))
    connection.close()
    assert cycle(cfg) == 0
    connection = open_db(cfg)
    assert get_job(connection, job_id) is None
    assert get_video(connection, video_id) is None
    connection.close()
    assert not video_dir(tmp_path, video_id).exists()
    assert not job_dir(tmp_path, job_id).exists()


def test_main_sleeps_when_idle_and_does_not_swallow_system_exit(monkeypatch):
    calls = {"n": 0}

    def fake_cycle(_settings, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        if calls["n"] == 2:
            return 1
        raise SystemExit(2)

    slept = []
    monkeypatch.setattr("backend.app.worker.cycle", fake_cycle)
    monkeypatch.setattr("backend.app.worker.time.sleep", lambda seconds: slept.append(seconds))
    with pytest.raises(SystemExit):
        main()
    assert slept == [0.5]
