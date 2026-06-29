"""Read models and queries for knowledge tags."""

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from techbrain.models import KnowledgeDocument, KnowledgeTag, knowledge_document_tags

TagSort = Literal["name", "-name", "usage_count", "-usage_count"]


@dataclass(frozen=True)
class PaginationResult:
    """Page metadata shared by tag query responses."""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_previous: bool
    has_next: bool


@dataclass(frozen=True)
class TagSummary:
    """Tag fields with active document usage count."""

    id: int
    name: str
    normalized_name: str
    status: str
    usage_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TagPage:
    """Paginated tag list."""

    items: tuple[TagSummary, ...]
    pagination: PaginationResult


@dataclass(frozen=True)
class TagDocumentSummary:
    """Document fields exposed from a tag association query."""

    id: int
    document_id: str
    title: str
    summary: str | None
    category_id: int
    category: str
    status: str
    source_updated_at: datetime
    relative_path: str


@dataclass(frozen=True)
class TagDocumentPage:
    """Paginated active documents associated with one tag."""

    items: tuple[TagDocumentSummary, ...]
    pagination: PaginationResult


def list_tags(
    session: Session,
    *,
    page: int,
    page_size: int,
    sort: TagSort,
) -> TagPage:
    """Return tags with accurate active-document usage counts."""
    usage_count = _usage_count_subquery()
    usage_value = func.coalesce(usage_count.c.usage_count, 0)
    statement = select(KnowledgeTag, usage_value.label("usage_count")).outerjoin(
        usage_count,
        usage_count.c.tag_id == KnowledgeTag.id,
    )
    statement = (
        statement.order_by(*_tag_order(sort, usage_value))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = session.execute(statement).all()
    total = int(session.scalar(select(func.count(KnowledgeTag.id))) or 0)
    return TagPage(
        items=tuple(_tag_summary(tag, count) for tag, count in rows),
        pagination=_pagination(page, page_size, total),
    )


def get_tag_detail(session: Session, tag_id: int) -> TagSummary | None:
    """Return one tag and its active document usage count."""
    usage_count = _usage_count_subquery()
    row = session.execute(
        select(KnowledgeTag, func.coalesce(usage_count.c.usage_count, 0))
        .outerjoin(usage_count, usage_count.c.tag_id == KnowledgeTag.id)
        .where(KnowledgeTag.id == tag_id)
    ).one_or_none()
    return _tag_summary(row[0], row[1]) if row is not None else None


def list_tag_documents(
    session: Session,
    tag_id: int,
    *,
    page: int,
    page_size: int,
) -> TagDocumentPage | None:
    """Return active documents directly associated with one tag."""
    if session.get(KnowledgeTag, tag_id) is None:
        return None

    association = knowledge_document_tags
    filters = (
        association.c.tag_id == tag_id,
        KnowledgeDocument.is_deleted.is_(False),
    )
    total = int(
        session.scalar(
            select(func.count(KnowledgeDocument.id))
            .select_from(
                association.join(
                    KnowledgeDocument,
                    KnowledgeDocument.id == association.c.document_id,
                )
            )
            .where(*filters)
        )
        or 0
    )
    documents = session.scalars(
        select(KnowledgeDocument)
        .join(association, association.c.document_id == KnowledgeDocument.id)
        .where(*filters)
        .order_by(
            KnowledgeDocument.source_updated_at.desc(),
            KnowledgeDocument.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return TagDocumentPage(
        items=tuple(_document_summary(document) for document in documents),
        pagination=_pagination(page, page_size, total),
    )


def _usage_count_subquery():
    association = knowledge_document_tags
    return (
        select(
            association.c.tag_id.label("tag_id"),
            func.count(KnowledgeDocument.id).label("usage_count"),
        )
        .join(KnowledgeDocument, KnowledgeDocument.id == association.c.document_id)
        .where(KnowledgeDocument.is_deleted.is_(False))
        .group_by(association.c.tag_id)
        .subquery()
    )


def _tag_order(sort: TagSort, usage_value) -> tuple:
    if sort == "name":
        return (KnowledgeTag.normalized_name.asc(), KnowledgeTag.id.asc())
    if sort == "-name":
        return (KnowledgeTag.normalized_name.desc(), KnowledgeTag.id.desc())
    if sort == "usage_count":
        return (usage_value.asc(), KnowledgeTag.normalized_name.asc(), KnowledgeTag.id.asc())
    return (usage_value.desc(), KnowledgeTag.normalized_name.asc(), KnowledgeTag.id.asc())


def _tag_summary(tag: KnowledgeTag, usage_count: int) -> TagSummary:
    return TagSummary(
        id=tag.id,
        name=tag.name,
        normalized_name=tag.normalized_name,
        status=tag.status,
        usage_count=int(usage_count),
        created_at=tag.created_at,
        updated_at=tag.updated_at,
    )


def _document_summary(document: KnowledgeDocument) -> TagDocumentSummary:
    return TagDocumentSummary(
        id=document.id,
        document_id=document.document_id,
        title=document.title,
        summary=document.summary,
        category_id=document.category_id,
        category=document.category,
        status=document.status,
        source_updated_at=document.source_updated_at,
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
