"""Error response schemas."""

from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """One field-level validation error."""

    field: str
    message: str
    type: str


class ErrorEnvelope(BaseModel):
    """Stable error payload."""

    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    """Top-level API error response."""

    error: ErrorEnvelope
    request_id: str
