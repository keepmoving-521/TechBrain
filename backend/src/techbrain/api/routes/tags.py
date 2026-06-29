"""Knowledge tag query endpoints."""

from typing import Literal

from fastapi import APIRouter, Query, Request, status
from starlette.exceptions import HTTPException

from techbrain.db.session import DatabaseManager
from techbrain.knowledge.tag_query import get_tag_detail, list_tag_documents, list_tags
from techbrain.schemas.tag import (
    TagDocumentListResponse,
    TagListResponse,
    TagSummaryResponse,
)

router = APIRouter()


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
