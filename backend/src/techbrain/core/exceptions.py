"""Unified API exception handling."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from techbrain.core.context import request_id_context
from techbrain.core.logging import get_logger
from techbrain.schemas.error import ErrorDetail, ErrorEnvelope, ErrorResponse

logger = get_logger(__name__)


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
    headers: dict[str, str] | None = None,
    request_id: str | None = None,
) -> JSONResponse:
    resolved_request_id = request_id or request_id_context.get()
    body = ErrorResponse(
        error=ErrorEnvelope(code=code, message=message, details=details),
        request_id=resolved_request_id,
    )
    response_headers = {"X-Request-ID": resolved_request_id, **(headers or {})}
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
        headers=response_headers,
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Normalize framework and application HTTP errors."""
    message = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    details = None if isinstance(exc.detail, str) else exc.detail
    return _error_response(
        status_code=exc.status_code,
        code=f"HTTP_{exc.status_code}",
        message=message,
        details=details,
        headers=exc.headers,
    )


async def validation_exception_handler(
    _: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return safe and stable validation error details."""
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"]),
            message=error["msg"],
            type=error["type"],
        ).model_dump()
        for error in exc.errors()
    ]
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="VALIDATION_ERROR",
        message="请求参数校验失败",
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Hide internal details while preserving them in server logs."""
    request_id = getattr(request.state, "request_id", request_id_context.get())
    logger.exception(
        "http.request.unhandled_exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "request_id": request_id,
        },
    )
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="服务器内部错误",
        request_id=request_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
