"""Knowledge tag and document-tag association models."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from techbrain.db.base import Base

if TYPE_CHECKING:
    from techbrain.models.knowledge_document import KnowledgeDocument

TAG_NAME_MAX_LENGTH = 80

knowledge_document_tags = Table(
    "knowledge_document_tags",
    Base.metadata,
    Column(
        "document_id",
        Integer,
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        Integer,
        ForeignKey("knowledge_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    ),
    Index("ix_knowledge_document_tags_tag_id", "tag_id"),
)


class KnowledgeTagStatus(StrEnum):
    """Knowledge tag lifecycle status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class KnowledgeTag(Base):
    """Normalized cross-category label assigned to knowledge documents."""

    __tablename__ = "knowledge_tags"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'archived')",
            name="ck_knowledge_tags_status",
        ),
        Index("ix_knowledge_tags_normalized_name", "normalized_name", unique=True),
        Index("ix_knowledge_tags_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(TAG_NAME_MAX_LENGTH), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(TAG_NAME_MAX_LENGTH), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeTagStatus.ACTIVE.value,
    )

    documents: Mapped[list[KnowledgeDocument]] = relationship(
        secondary=knowledge_document_tags,
        back_populates="tag_nodes",
    )

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

    @validates("name")
    def _validate_name(self, _: str, name: str) -> str:
        display_name = validate_tag_name(name)
        self.normalized_name = normalize_tag_name(display_name)
        return display_name

    @validates("status")
    def _validate_status(self, _: str, status: str) -> str:
        return KnowledgeTagStatus(status).value


def normalize_tag_name(name: str) -> str:
    """Return the stable uniqueness key for a tag name."""
    normalized_unicode = unicodedata.normalize("NFKC", name)
    collapsed_whitespace = " ".join(normalized_unicode.strip().split())
    return collapsed_whitespace.casefold()


def validate_tag_name(name: str) -> str:
    """Validate and return a normalized display name without changing its case."""
    normalized_unicode = unicodedata.normalize("NFKC", name)
    if any(unicodedata.category(char).startswith("C") for char in normalized_unicode):
        raise ValueError("标签名称不能包含控制字符")
    display_name = " ".join(normalized_unicode.strip().split())
    if not display_name:
        raise ValueError("标签名称不能为空")
    if len(display_name) > TAG_NAME_MAX_LENGTH:
        raise ValueError(f"标签名称不能超过 {TAG_NAME_MAX_LENGTH} 个字符")
    normalized_name = display_name.casefold()
    if len(normalized_name) > TAG_NAME_MAX_LENGTH:
        raise ValueError(f"标签规范化名称不能超过 {TAG_NAME_MAX_LENGTH} 个字符")
    return display_name
