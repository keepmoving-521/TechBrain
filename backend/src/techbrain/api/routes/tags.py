"""Knowledge tag query endpoints."""

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock
from typing import Literal

from fastapi import APIRouter, Query, Request, Response, status
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from techbrain.core.config import Settings
from techbrain.db.session import DatabaseManager
from techbrain.knowledge.tag_management import (
    TagConflictError,
    TagNotFoundError,
    TagValidationError,
    create_tag,
    delete_tag,
    rename_tag,
)
from techbrain.knowledge.tag_query import get_tag_detail, list_tag_documents, list_tags
from techbrain.schemas.tag import (
    TagCreateRequest,
    TagDocumentListResponse,
    TagListResponse,
    TagSummaryResponse,
    TagUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=TagSummaryResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_tag(request: Request, payload: TagCreateRequest) -> TagSummaryResponse:
    """Create one unused active tag."""
    database: DatabaseManager = request.app.state.database
    with _knowledge_write_lock(request), database.session_factory() as session:
        try:
            tag = create_tag(session, payload.name)
        except TagValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except TagConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return _tag_response(session, tag.id)


@router.patch("/{tag_id}", response_model=TagSummaryResponse)
def rename_knowledge_tag(
    request: Request,
    tag_id: int,
    payload: TagUpdateRequest,
) -> TagSummaryResponse:
    """Rename a tag and safely write the new name to associated Markdown files."""
    database: DatabaseManager = request.app.state.database
    settings: Settings = request.app.state.settings
    with _knowledge_write_lock(request), database.session_factory() as session:
        try:
            tag = rename_tag(session, settings, tag_id, payload.name)
        except TagNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except TagValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except TagConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return _tag_response(session, tag.id)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_tag(request: Request, tag_id: int) -> Response:
    """Delete one tag only when no document uses it."""
    database: DatabaseManager = request.app.state.database
    with _knowledge_write_lock(request), database.session_factory() as session:
        try:
            delete_tag(session, tag_id)
        except TagNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except TagConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=TagListResponse)
def get_tags(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: Literal["name", "-name", "usage_count", "-usage_count"] = "name",
) -> TagListResponse:
    """Return a paginated tag list sorted by name or usage count."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        result = list_tags(session, page=page, page_size=page_size, sort=sort)
        return TagListResponse.model_validate(result, from_attributes=True)


@router.get("/{tag_id}/documents", response_model=TagDocumentListResponse)
def get_tag_documents(
    request: Request,
    tag_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TagDocumentListResponse:
    """Return active documents associated with one tag."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        result = list_tag_documents(session, tag_id, page=page, page_size=page_size)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
        return TagDocumentListResponse.model_validate(result, from_attributes=True)


@router.get("/{tag_id}", response_model=TagSummaryResponse)
def get_tag(request: Request, tag_id: int) -> TagSummaryResponse:
    """Return one tag and its active document usage count."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        result = get_tag_detail(session, tag_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
        return TagSummaryResponse.model_validate(result)


def _tag_response(session: Session, tag_id: int) -> TagSummaryResponse:
    result = get_tag_detail(session, tag_id)
    if result is None:  # pragma: no cover - committed tag must exist
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    return TagSummaryResponse.model_validate(result)


@contextmanager
def _knowledge_write_lock(request: Request) -> Iterator[None]:
    sync_lock: Lock = request.app.state.knowledge_sync_lock
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="知识库同步或元数据变更正在执行, 请稍后再试",
        )
    try:
        yield
    finally:
        sync_lock.release()
