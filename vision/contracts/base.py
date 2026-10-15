"""Shared validation conventions for versioned, transport-independent contracts."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[str, Field(min_length=1, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]
NonNegativeInt = Annotated[int, Field(ge=0)]
Seconds = Annotated[float, Field(ge=0)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class Contract(BaseModel):
    """Frozen fields, immutable collections, finite numbers and no unknown fields."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        allow_inf_nan=False,
        validate_default=True,
    )
