"""Knowledge document list endpoints."""

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query, Request, status
from starlette.exceptions import HTTPException

from techbrain.db.session import DatabaseManager
from techbrain.knowledge.document_query import list_documents, parse_status_filter
from techbrain.schemas.document import DocumentListResponse

router = APIRouter()


@router.get("", response_model=DocumentListResponse)
def get_documents(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category_id: int | None = Query(default=None, ge=1),
    tag_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    updated_from: datetime | None = None,
    updated_to: datetime | None = None,
    sort: Literal["updated_at", "-updated_at"] = "-updated_at",
) -> DocumentListResponse:
    """Return filtered active documents with stable pagination and ordering."""
    try:
        statuses = parse_status_filter(status_filter)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if updated_from is not None and updated_to is not None and updated_from > updated_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="updated_from 不能晚于 updated_to",
        )

    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        result = list_documents(
            session,
            page=page,
            page_size=page_size,
            category_id=category_id,
            tag_id=tag_id,
            statuses=statuses,
            updated_from=updated_from,
            updated_to=updated_to,
            sort=sort,
        )
        return DocumentListResponse.model_validate(result, from_attributes=True)
