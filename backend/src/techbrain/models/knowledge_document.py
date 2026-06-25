"""Knowledge document ORM model."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from techbrain.db.base import Base


class KnowledgeDocumentStatus(StrEnum):
    """Document lifecycle status from Front Matter."""

    PUBLISHED = "published"
    DRAFT = "draft"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class DocumentVisibility(StrEnum):
    """Document visibility scope."""

    PRIVATE = "private"
    SHARED = "shared"


class DocumentSyncStatus(StrEnum):
    """Latest synchronization status for a document row."""

    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    DELETED = "deleted"


class KnowledgeDocument(Base):
    """Structured metadata for one Markdown knowledge document.

    `document_id` comes from Front Matter and stays stable when the file moves.
    `relative_path` records the current source path under the knowledge root.
    """

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        CheckConstraint(
            "status in ('published', 'draft', 'archived', 'deprecated')",
            name="ck_knowledge_documents_status",
        ),
        CheckConstraint(
            "visibility in ('private', 'shared')",
            name="ck_knowledge_documents_visibility",
        ),
        CheckConstraint(
            "sync_status in ('pending', 'synced', 'failed', 'deleted')",
            name="ck_knowledge_documents_sync_status",
        ),
        Index("ix_knowledge_documents_document_id", "document_id", unique=True),
        Index("ix_knowledge_documents_relative_path", "relative_path", unique=True),
        Index("ix_knowledge_documents_path_hash", "path_hash"),
        Index("ix_knowledge_documents_content_hash", "content_hash"),
        Index("ix_knowledge_documents_status", "status"),
        Index("ix_knowledge_documents_sync_status", "sync_status"),
        Index("ix_knowledge_documents_is_deleted", "is_deleted"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    document_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="published")
    visibility: Mapped[str] = mapped_column(String(32), nullable=False, default="private")
    language: Mapped[str] = mapped_column(String(32), nullable=False, default="zh-CN")

    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    absolute_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    path_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    front_matter_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    source_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    sync_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
