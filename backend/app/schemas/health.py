from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok"] = "ok"
    service: Literal["intelligent-traffic-tracking-api"] = "intelligent-traffic-tracking-api"
    api_version: Literal["v1"] = "v1"
