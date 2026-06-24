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
    database_check = request.app.state.database.check_connection()
    checks = [
        ReadinessCheck(name="configuration", status="ok"),
        ReadinessCheck(
            name="database",
            status="ok" if database_check.ok else "error",
            message=database_check.message,
        ),
    ]
    readiness_status = "ok" if all(check.status == "ok" for check in checks) else "error"
    response = ReadinessResponse(
        status=readiness_status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        checks=checks,
    )
    if readiness_status == "error":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(mode="json"),
        )
    return response
