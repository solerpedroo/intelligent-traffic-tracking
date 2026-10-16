"""Verify actual ASGI transport, configuration and CORS without loading models."""

import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.main import create_app


@pytest.fixture
def client():
    with TestClient(create_app(Settings())) as client:
        yield client


def test_health_reports_liveness_only(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "intelligent-traffic-tracking-api",
        "api_version": "v1",
    }
    paths = set(client.get("/openapi.json").json()["paths"])
    assert "/api/health" in paths and "/api/jobs" in paths
    assert client.post("/api/jobs", json={}).status_code == 422


def test_cors_allows_configured_local_origin_only(client):
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    denied = client.get("/api/health", headers={"Origin": "https://untrusted.example"})
    assert "access-control-allow-origin" not in denied.headers
    preflight = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_settings_read_environment_and_normalize_origins(monkeypatch):
    monkeypatch.setenv("TRAFFIC_ALLOWED_ORIGINS", '["http://localhost:4321"]')
    monkeypatch.setenv("TRAFFIC_LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert str(settings.allowed_origins[0]) == "http://localhost:4321/"
    assert settings.log_level == "DEBUG"
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/health", headers={"Origin": "http://localhost:4321"})
        assert response.headers["access-control-allow-origin"] == "http://localhost:4321"


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "file:///tmp",
        "https://host.example/path",
        "https://user:secret@host.example",
        "https://host.example/?x=y",
    ],
)
def test_settings_reject_non_origin_values(monkeypatch, origin):
    import json

    monkeypatch.setenv("TRAFFIC_ALLOWED_ORIGINS", json.dumps([origin]))
    with pytest.raises(ValidationError):
        Settings()


def test_settings_reject_invalid_log_level(monkeypatch):
    monkeypatch.setenv("TRAFFIC_LOG_LEVEL", "VERBOSE")
    with pytest.raises(ValidationError):
        Settings()


def test_api_startup_does_not_import_scientific_dependencies():
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            """
import sys
from backend.app.main import app
for name in ('vision', 'numpy', 'torch', 'cv2', 'ultralytics'):
    assert name not in sys.modules, name
""",
        ],
        check=True,
    )
