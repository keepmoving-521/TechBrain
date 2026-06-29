"""Paginated filtering and sorting queries for knowledge documents."""

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from techbrain.models import KnowledgeDocument, knowledge_document_tags

DocumentSort = Literal["updated_at", "-updated_at"]
DEFAULT_DOCUMENT_STATUSES = ("published", "deprecated")
VALID_DOCUMENT_STATUSES = {"published", "draft", "archived", "deprecated"}


@dataclass(frozen=True)
class PaginationResult:
    """Standard page metadata."""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_previous: bool
    has_next: bool


@dataclass(frozen=True)
class DocumentListItem:
    """Document fields returned by the knowledge list endpoint."""

    id: int
    document_id: str
    title: str
    summary: str | None
    category_id: int
    category: str
    tags: tuple[str, ...]
    status: str
    visibility: str
    language: str
    created_at: datetime
    updated_at: datetime
    relative_path: str


@dataclass(frozen=True)
class DocumentPage:
    """Paginated knowledge document list."""

    items: tuple[DocumentListItem, ...]
    pagination: PaginationResult


class DocumentNotFoundError(LookupError):
    """Raised when a document primary key does not exist."""


class DocumentDeletedError(LookupError):
    """Raised when a document exists but has been soft deleted."""


@dataclass(frozen=True)
class DocumentSyncInfo:
    """Latest synchronization state and integrity hashes."""

    status: str
    error: str | None
    last_scanned_at: datetime | None
    last_synced_at: datetime | None
    path_hash: str
    content_hash: str
    front_matter_hash: str


@dataclass(frozen=True)
class DocumentDetail:
    """Complete active document content, metadata and synchronization state."""

    id: int
    document_id: str
    title: str
    summary: str | None
    body: str
    category_id: int
    category: str
    tags: tuple[str, ...]
    aliases: tuple[str, ...]
    status: str
    visibility: str
    language: str
    source: dict[str, Any]
    relative_path: str
    created_at: datetime
    updated_at: datetime
    sync: DocumentSyncInfo
    record_created_at: datetime
    record_updated_at: datetime


def parse_status_filter(value: str | None) -> tuple[str, ...] | None:
    """Parse a comma-separated status filter and reject unknown values."""
    if value is None:
        return None
    statuses = tuple(dict.fromkeys(item.strip() for item in value.split(",") if item.strip()))
    if not statuses:
        raise ValueError("status 至少需要包含一个文档状态")
    invalid = sorted(set(statuses) - VALID_DOCUMENT_STATUSES)
    if invalid:
        raise ValueError(f"不支持的文档状态: {', '.join(invalid)}")
    return statuses


def list_documents(
    session: Session,
    *,
    page: int,
    page_size: int,
    category_id: int | None,
    tag_id: int | None,
    statuses: tuple[str, ...] | None,
    updated_from: datetime | None,
    updated_to: datetime | None,
    sort: DocumentSort,
) -> DocumentPage:
    """Return filtered active documents using stable source-update ordering."""
    effective_statuses = statuses or DEFAULT_DOCUMENT_STATUSES
    filters = [
        KnowledgeDocument.is_deleted.is_(False),
        KnowledgeDocument.status.in_(effective_statuses),
    ]
    if category_id is not None:
        filters.append(KnowledgeDocument.category_id == category_id)
    if updated_from is not None:
        filters.append(KnowledgeDocument.source_updated_at >= updated_from)
    if updated_to is not None:
        filters.append(KnowledgeDocument.source_updated_at <= updated_to)

    statement = select(KnowledgeDocument)
    count_statement = select(func.count(KnowledgeDocument.id))
    if tag_id is not None:
        statement = statement.join(
            knowledge_document_tags,
            knowledge_document_tags.c.document_id == KnowledgeDocument.id,
        )
        count_statement = count_statement.join(
            knowledge_document_tags,
            knowledge_document_tags.c.document_id == KnowledgeDocument.id,
        )
        filters.append(knowledge_document_tags.c.tag_id == tag_id)

    total = int(session.scalar(count_statement.where(*filters)) or 0)
    documents = session.scalars(
        statement.where(*filters)
        .order_by(*_document_order(sort))
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentPage(
        items=tuple(_document_item(document) for document in documents),
        pagination=_pagination(page, page_size, total),
    )


def get_document_detail(session: Session, document_id: int) -> DocumentDetail:
    """Return one active document or a distinct missing/deleted error."""
    document = session.get(KnowledgeDocument, document_id)
    if document is None:
        raise DocumentNotFoundError("文档不存在")
    if document.is_deleted:
        raise DocumentDeletedError("文档已删除")
    return DocumentDetail(
        id=document.id,
        document_id=document.document_id,
        title=document.title,
        summary=document.summary,
        body=document.body,
        category_id=document.category_id,
        category=document.category,
        tags=tuple(document.tags),
        aliases=tuple(document.aliases),
        status=document.status,
        visibility=document.visibility,
        language=document.language,
        source=dict(document.source),
        relative_path=document.relative_path,
        created_at=document.source_created_at,
        updated_at=document.source_updated_at,
        sync=DocumentSyncInfo(
            status=document.sync_status,
            error=document.sync_error,
            last_scanned_at=document.last_scanned_at,
            last_synced_at=document.last_synced_at,
            path_hash=document.path_hash,
            content_hash=document.content_hash,
            front_matter_hash=document.front_matter_hash,
        ),
        record_created_at=document.created_at,
        record_updated_at=document.updated_at,
    )


def _document_order(sort: DocumentSort) -> tuple:
    if sort == "updated_at":
        return (
            KnowledgeDocument.source_updated_at.asc(),
            KnowledgeDocument.id.asc(),
        )
    return (
        KnowledgeDocument.source_updated_at.desc(),
        KnowledgeDocument.id.desc(),
    )


def _document_item(document: KnowledgeDocument) -> DocumentListItem:
    return DocumentListItem(
        id=document.id,
        document_id=document.document_id,
        title=document.title,
        summary=document.summary,
        category_id=document.category_id,
        category=document.category,
        tags=tuple(document.tags),
        status=document.status,
        visibility=document.visibility,
        language=document.language,
        created_at=document.source_created_at,
        updated_at=document.source_updated_at,
        relative_path=document.relative_path,
    )


def _pagination(page: int, page_size: int, total: int) -> PaginationResult:
    total_pages = ceil(total / page_size) if total else 0
    return PaginationResult(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_previous=page > 1,
        has_next=page < total_pages,
    )
