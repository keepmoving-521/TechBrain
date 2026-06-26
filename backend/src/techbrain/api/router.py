"""Root API router."""

from fastapi import APIRouter

from techbrain.api.routes.health import router as health_router
from techbrain.api.routes.knowledge_sync import router as knowledge_sync_router

api_router = APIRouter()
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(knowledge_sync_router, prefix="/knowledge/sync", tags=["knowledge-sync"])
