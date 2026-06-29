"""Knowledge category query endpoints."""

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock

from fastapi import APIRouter, Request, Response, status
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException

from techbrain.core.config import Settings
from techbrain.db.session import DatabaseManager
from techbrain.knowledge.category_management import (
    CategoryConflictError,
    CategoryNotFoundError,
    CategoryValidationError,
    create_category,
    delete_category,
    migrate_category_documents,
    update_category,
)
from techbrain.knowledge.category_query import get_category_detail, list_category_tree
from techbrain.models import KnowledgeCategory
from techbrain.schemas.category import (
    CategoryCreateRequest,
    CategoryDetailResponse,
    CategoryDocumentMigrationRequest,
    CategoryDocumentMigrationResponse,
    CategoryTreeResponse,
    CategoryUpdateRequest,
)

router = APIRouter()


@router.post("", response_model=CategoryDetailResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_category(
    request: Request,
    payload: CategoryCreateRequest,
) -> CategoryDetailResponse:
    """Create one empty knowledge category."""
    database: DatabaseManager = request.app.state.database
    with _category_write_lock(request), database.session_factory() as session:
        category = _create_category_or_http_error(session, payload)
        return _category_detail_response(session, category.id)


@router.patch("/{category_id}", response_model=CategoryDetailResponse)
def update_knowledge_category(
    request: Request,
    category_id: int,
    payload: CategoryUpdateRequest,
) -> CategoryDetailResponse:
    """Rename, move or reorder a category with safe Markdown write-back."""
    database: DatabaseManager = request.app.state.database
    settings: Settings = request.app.state.settings
    fields = payload.model_fields_set
    arguments = {
        field_name: getattr(payload, field_name)
        for field_name in ("name", "slug", "parent_id", "sort_order")
        if field_name in fields
    }
    with _category_write_lock(request), database.session_factory() as session:
        try:
            category = update_category(session, settings, category_id, **arguments)
        except CategoryNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except CategoryValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except CategoryConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return _category_detail_response(session, category.id)


@router.post(
    "/{category_id}/documents/migrate",
    response_model=CategoryDocumentMigrationResponse,
)
def migrate_knowledge_category_documents(
    request: Request,
    category_id: int,
    payload: CategoryDocumentMigrationRequest,
) -> CategoryDocumentMigrationResponse:
    """Move all documents directly assigned to a category."""
    database: DatabaseManager = request.app.state.database
    settings: Settings = request.app.state.settings
    with _category_write_lock(request), database.session_factory() as session:
        try:
            result = migrate_category_documents(
                session,
                settings,
                category_id,
                payload.target_category_id,
            )
        except CategoryNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except CategoryValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except CategoryConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return CategoryDocumentMigrationResponse.model_validate(result)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_category(request: Request, category_id: int) -> Response:
    """Delete an empty leaf category."""
    database: DatabaseManager = request.app.state.database
    with _category_write_lock(request), database.session_factory() as session:
        try:
            delete_category(session, category_id)
        except CategoryNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except CategoryConflictError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tree", response_model=CategoryTreeResponse)
def get_category_tree(request: Request) -> CategoryTreeResponse:
    """Return the complete category tree with active document counts."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        nodes = list_category_tree(session)
        return CategoryTreeResponse(items=list(nodes))


@router.get("/{category_id}", response_model=CategoryDetailResponse)
def get_category(request: Request, category_id: int) -> CategoryDetailResponse:
    """Return one category with immediate parent and child navigation."""
    database: DatabaseManager = request.app.state.database
    with database.session_factory() as session:
        category = get_category_detail(session, category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类不存在",
            )
        return CategoryDetailResponse.model_validate(category)


def _create_category_or_http_error(
    session: Session,
    payload: CategoryCreateRequest,
) -> KnowledgeCategory:
    try:
        return create_category(
            session,
            name=payload.name,
            slug=payload.slug,
            parent_id=payload.parent_id,
            sort_order=payload.sort_order,
        )
    except CategoryNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except CategoryValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CategoryConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _category_detail_response(session: Session, category_id: int) -> CategoryDetailResponse:
    detail = get_category_detail(session, category_id)
    if detail is None:  # pragma: no cover - committed category must exist
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    return CategoryDetailResponse.model_validate(detail)


@contextmanager
def _category_write_lock(request: Request) -> Iterator[None]:
    sync_lock: Lock = request.app.state.knowledge_sync_lock
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="知识库同步或分类变更正在执行, 请稍后再试",
        )
    try:
        yield
    finally:
        sync_lock.release()
