"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from threading import Lock

from fastapi import FastAPI

from techbrain.api.router import api_router
from techbrain.core.config import Settings, get_settings
from techbrain.core.exceptions import register_exception_handlers
from techbrain.core.logging import configure_logging, get_logger
from techbrain.core.middleware import RequestContextMiddleware
from techbrain.db.session import DatabaseManager
from techbrain.knowledge.scheduler import KnowledgeSyncScheduler


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create a configured TechBrain API application."""
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)
    logger = get_logger(__name__)
    database = DatabaseManager(resolved_settings)
    knowledge_sync_lock = Lock()
    knowledge_sync_scheduler = KnowledgeSyncScheduler(
        resolved_settings,
        database,
        knowledge_sync_lock,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application.started",
            extra={
                "environment": resolved_settings.environment.value,
                "version": resolved_settings.app_version,
            },
        )
        knowledge_sync_scheduler.start()
        try:
            yield
        finally:
            knowledge_sync_scheduler.stop()
            database.dispose()
            logger.info("application.stopped")

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.debug,
        docs_url="/docs" if resolved_settings.docs_enabled else None,
        redoc_url="/redoc" if resolved_settings.docs_enabled else None,
        openapi_url="/openapi.json" if resolved_settings.docs_enabled else None,
        lifespan=lifespan,
    )
    application.state.settings = resolved_settings
    application.state.database = database
    application.state.knowledge_sync_lock = knowledge_sync_lock
    application.state.knowledge_sync_scheduler = knowledge_sync_scheduler
    application.add_middleware(RequestContextMiddleware)
    register_exception_handlers(application)
    application.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    return application
