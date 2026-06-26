"""Knowledge synchronization management endpoints."""

from threading import Lock

from fastapi import APIRouter, Request, status
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException

from techbrain.core.config import Settings
from techbrain.db.session import DatabaseManager
from techbrain.knowledge.config import (
    KnowledgeConfigurationError,
    build_knowledge_repository_config,
)
from techbrain.knowledge.task import (
    get_sync_task_statement,
    list_sync_tasks_statement,
    run_full_knowledge_sync,
)
from techbrain.models import KnowledgeSyncTask
from techbrain.schemas.knowledge_sync import (
    KnowledgeSyncScheduleResponse,
    KnowledgeSyncScheduleUpdateRequest,
    KnowledgeSyncTaskListResponse,
    KnowledgeSyncTaskResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=KnowledgeSyncTaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def trigger_knowledge_sync(request: Request) -> KnowledgeSyncTaskResponse:
    """Trigger one full Markdown knowledge synchronization task."""
    sync_lock: Lock = request.app.state.knowledge_sync_lock
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="知识库同步任务正在执行, 请稍后再试",
        )

    try:
        settings: Settings = request.app.state.settings
        database: DatabaseManager = request.app.state.database
        try:
            config = build_knowledge_repository_config(settings)
        except KnowledgeConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

        with database.session_factory() as session:
            result = run_full_knowledge_sync(session, config)
            task = _get_task_or_404(session, result.task_id or 0)
            return KnowledgeSyncTaskResponse.model_validate(task)
    finally:
        sync_lock.release()


@router.get("/schedule", response_model=KnowledgeSyncScheduleResponse)
def get_knowledge_sync_schedule(request: Request) -> KnowledgeSyncScheduleResponse:
    """Get periodic knowledge synchronization runtime configuration."""
    scheduler = request.app.state.knowledge_sync_scheduler
    return KnowledgeSyncScheduleResponse.model_validate(scheduler.get_state())


@router.put("/schedule", response_model=KnowledgeSyncScheduleResponse)
def update_knowledge_sync_schedule(
    request: Request,
    payload: KnowledgeSyncScheduleUpdateRequest,
) -> KnowledgeSyncScheduleResponse:
    """Update periodic knowledge synchronization runtime configuration."""
    scheduler = request.app.state.knowledge_sync_scheduler
    try:
        state = scheduler.update(
            enabled=payload.enabled,
            interval_seconds=payload.interval_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return KnowledgeSyncScheduleResponse.model_validate(state)


@router.get("/tasks", response_model=KnowledgeSyncTaskListResponse)
def list_knowledge_sync_tasks(request: Request) -> KnowledgeSyncTaskListResponse:
    """List knowledge synchronization task history."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        tasks = session.scalars(
            list_sync_tasks_statement().options(selectinload(KnowledgeSyncTask.failures))
        ).all()
        return KnowledgeSyncTaskListResponse(
            items=[KnowledgeSyncTaskResponse.model_validate(task) for task in tasks]
        )


@router.get("/tasks/{task_id}", response_model=KnowledgeSyncTaskResponse)
def get_knowledge_sync_task(request: Request, task_id: int) -> KnowledgeSyncTaskResponse:
    """Get one knowledge synchronization task with failure details."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        task = _get_task_or_404(session, task_id)
        return KnowledgeSyncTaskResponse.model_validate(task)


def _get_task_or_404(session, task_id: int) -> KnowledgeSyncTask:
    task = session.scalar(
        get_sync_task_statement(task_id).options(selectinload(KnowledgeSyncTask.failures))
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="同步任务不存在",
        )
    return task
