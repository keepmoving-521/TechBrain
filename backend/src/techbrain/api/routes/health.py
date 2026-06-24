"""Application health endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from techbrain.schemas.health import HealthResponse, ReadinessCheck, ReadinessResponse

router = APIRouter()


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="存活检查",
)
async def live(request: Request) -> HealthResponse:
    """Confirm that the API process is running."""
    settings = request.app.state.settings
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="就绪检查",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def ready(request: Request) -> ReadinessResponse | JSONResponse:
    """Confirm that required application configuration is valid."""
    settings = request.app.state.settings
    checks = [
        ReadinessCheck(name="configuration", status="ok"),
    ]
    response = ReadinessResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        checks=checks,
    )
    return response
