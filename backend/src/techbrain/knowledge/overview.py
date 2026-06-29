"""Aggregated read model for the knowledge homepage."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from techbrain.models import (
    KnowledgeCategory,
    KnowledgeDocument,
    KnowledgeTag,
    knowledge_document_tags,
)

VISIBLE_DOCUMENT_STATUSES = ("published", "deprecated")
DEFAULT_SECTION_LIMIT = 6


@dataclass(frozen=True)
class OverviewStatistics:
    """Counts displayed in the homepage summary cards."""

    document_count: int
    published_document_count: int
    draft_document_count: int
    category_count: int
    tag_count: int


@dataclass(frozen=True)
class RecentDocument:
    """A recently updated browsable document."""

    id: int
    document_id: str
    title: str
    summary: str | None
    category_id: int
    category: str
    tags: tuple[str, ...]
    status: str
    updated_at: datetime


@dataclass(frozen=True)
class PopularCategory:
    """An active category ranked by direct browsable document usage."""

    id: int
    name: str
    path: str
    document_count: int


@dataclass(frozen=True)
class PopularTag:
    """An active tag ranked by browsable document usage."""

    id: int
    name: str
    usage_count: int


@dataclass(frozen=True)
class KnowledgeOverview:
    """Complete homepage payload."""

    is_empty: bool
    statistics: OverviewStatistics
    recent_documents: tuple[RecentDocument, ...]
    popular_categories: tuple[PopularCategory, ...]
    popular_tags: tuple[PopularTag, ...]


def get_knowledge_overview(
    session: Session,
    *,
    section_limit: int = DEFAULT_SECTION_LIMIT,
) -> KnowledgeOverview:
    """Return accurate knowledge counts and ranked homepage entries."""
    document_count = _count_documents(session)
    published_document_count = _count_documents(session, statuses=VISIBLE_DOCUMENT_STATUSES)
    statistics = OverviewStatistics(
        document_count=document_count,
        published_document_count=published_document_count,
        draft_document_count=_count_documents(session, statuses=("draft",)),
        category_count=_count_active_categories(session),
        tag_count=_count_active_tags(session),
    )
    return KnowledgeOverview(
        is_empty=document_count == 0,
        statistics=statistics,
        recent_documents=_recent_documents(session, section_limit),
        popular_categories=_popular_categories(session, section_limit),
        popular_tags=_popular_tags(session, section_limit),
    )


def _count_documents(session: Session, *, statuses: tuple[str, ...] | None = None) -> int:
    filters = [KnowledgeDocument.is_deleted.is_(False)]
    if statuses is not None:
        filters.append(KnowledgeDocument.status.in_(statuses))
    return int(session.scalar(select(func.count(KnowledgeDocument.id)).where(*filters)) or 0)


def _count_active_categories(session: Session) -> int:
    return int(
        session.scalar(
            select(func.count(KnowledgeCategory.id)).where(KnowledgeCategory.status == "active")
        )
        or 0
    )


def _count_active_tags(session: Session) -> int:
    return int(
        session.scalar(select(func.count(KnowledgeTag.id)).where(KnowledgeTag.status == "active"))
        or 0
    )


def _recent_documents(session: Session, limit: int) -> tuple[RecentDocument, ...]:
    documents = session.scalars(
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.is_deleted.is_(False),
            KnowledgeDocument.status.in_(VISIBLE_DOCUMENT_STATUSES),
        )
        .order_by(KnowledgeDocument.source_updated_at.desc(), KnowledgeDocument.id.desc())
        .limit(limit)
    ).all()
    return tuple(
        RecentDocument(
            id=document.id,
            document_id=document.document_id,
            title=document.title,
            summary=document.summary,
            category_id=document.category_id,
            category=document.category,
            tags=tuple(document.tags),
            status=document.status,
            updated_at=document.source_updated_at,
        )
        for document in documents
    )


def _popular_categories(session: Session, limit: int) -> tuple[PopularCategory, ...]:
    usage_counts = (
        select(
            KnowledgeDocument.category_id.label("category_id"),
            func.count(KnowledgeDocument.id).label("document_count"),
        )
        .where(
            KnowledgeDocument.is_deleted.is_(False),
            KnowledgeDocument.status.in_(VISIBLE_DOCUMENT_STATUSES),
        )
        .group_by(KnowledgeDocument.category_id)
        .subquery()
    )
    rows = session.execute(
        select(KnowledgeCategory, usage_counts.c.document_count)
        .join(usage_counts, usage_counts.c.category_id == KnowledgeCategory.id)
        .where(KnowledgeCategory.status == "active")
        .order_by(
            usage_counts.c.document_count.desc(),
            KnowledgeCategory.sort_order.asc(),
            KnowledgeCategory.id.asc(),
        )
        .limit(limit)
    ).all()
    return tuple(
        PopularCategory(
            id=category.id,
            name=category.name,
            path=category.path,
            document_count=int(document_count),
        )
        for category, document_count in rows
    )


def _popular_tags(session: Session, limit: int) -> tuple[PopularTag, ...]:
    association = knowledge_document_tags
    usage_counts = (
        select(
            association.c.tag_id.label("tag_id"),
            func.count(KnowledgeDocument.id).label("usage_count"),
        )
        .join(KnowledgeDocument, KnowledgeDocument.id == association.c.document_id)
        .where(
            KnowledgeDocument.is_deleted.is_(False),
            KnowledgeDocument.status.in_(VISIBLE_DOCUMENT_STATUSES),
        )
        .group_by(association.c.tag_id)
        .subquery()
    )
    rows = session.execute(
        select(KnowledgeTag, usage_counts.c.usage_count)
        .join(usage_counts, usage_counts.c.tag_id == KnowledgeTag.id)
        .where(KnowledgeTag.status == "active")
        .order_by(
            usage_counts.c.usage_count.desc(),
            KnowledgeTag.normalized_name.asc(),
            KnowledgeTag.id.asc(),
        )
        .limit(limit)
    ).all()
    return tuple(
        PopularTag(id=tag.id, name=tag.name, usage_count=int(usage_count))
        for tag, usage_count in rows
    )
