"""Health endpoint schemas."""

from typing import Literal

from pydantic import BaseModel

from techbrain.core.config import Environment


class HealthResponse(BaseModel):
    """API process health."""

    status: Literal["ok", "error"]
    service: str
    version: str
    environment: Environment


class ReadinessCheck(BaseModel):
    """One readiness dependency check."""

    name: str
    status: Literal["ok", "error"]
    message: str | None = None


class ReadinessResponse(HealthResponse):
    """API readiness including dependency checks."""

    checks: list[ReadinessCheck]
