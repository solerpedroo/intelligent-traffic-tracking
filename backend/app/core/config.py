"""Local server settings; values are injected into the app factory."""

from typing import Literal

from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRAFFIC_", extra="forbid", frozen=True)

    allowed_origins: tuple[HttpUrl, ...] = (
        HttpUrl("http://localhost:3000"),
        HttpUrl("http://127.0.0.1:3000"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, origins: tuple[HttpUrl, ...]) -> tuple[HttpUrl, ...]:
        for origin in origins:
            if (
                origin.username is not None
                or origin.password is not None
                or origin.path not in (None, "/")
                or origin.query is not None
                or origin.fragment is not None
            ):
                raise ValueError("CORS origins must contain only a scheme, host and optional port")
        return origins
