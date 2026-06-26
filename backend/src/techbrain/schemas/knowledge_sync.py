"""Knowledge synchronization API schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeSyncFailureResponse(BaseModel):
    """Synchronization failure response."""

    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    path: str
    stage: str
    code: str
    message: str
    field: str | None = None
    line: int | None = None
    column: int | None = None


class KnowledgeSyncTaskResponse(BaseModel):
    """Synchronization task response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    started_at: datetime
    finished_at: datetime
    scanned_count: int
    success_count: int
    failed_count: int
    created_count: int
    updated_count: int
    restored_count: int
    unchanged_count: int
    deleted_count: int
    failures: list[KnowledgeSyncFailureResponse] = []


class KnowledgeSyncTaskListResponse(BaseModel):
    """Synchronization task list response."""

    items: list[KnowledgeSyncTaskResponse]


class KnowledgeSyncScheduleResponse(BaseModel):
    """Periodic synchronization schedule response."""

    model_config = ConfigDict(from_attributes=True)

    enabled: bool
    interval_seconds: int
    running: bool
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_task_id: int | None = None
    last_error: str | None = None


class KnowledgeSyncScheduleUpdateRequest(BaseModel):
    """Periodic synchronization schedule update request."""

    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=60)
