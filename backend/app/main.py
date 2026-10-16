"""Liveness-only foundation. No detector, worker, storage or video initialization."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import Settings
from backend.app.routes import install
from backend.app.schemas.health import HealthResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings()
    logging.getLogger("traffic").setLevel(settings.log_level)
    app = FastAPI(title="Intelligent Traffic Tracking API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.allowed_origins],
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type"],
        allow_credentials=False,
    )

    @app.get("/api/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        """Service liveness only; does not imply model or worker readiness."""
        return HealthResponse()

    install(app, settings)
    return app


app = create_app()
