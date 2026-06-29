"""Knowledge category ORM model."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from techbrain.db.base import Base

CATEGORY_NAME_MAX_LENGTH = 80
CATEGORY_SLUG_MAX_LENGTH = 80
CATEGORY_PATH_MAX_LENGTH = 512

_SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")


class KnowledgeCategoryStatus(StrEnum):
    """Knowledge category lifecycle status."""

    ACTIVE = "active"
    HIDDEN = "hidden"
    ARCHIVED = "archived"


class KnowledgeCategory(Base):
    """Hierarchical category for organizing knowledge documents."""

    __tablename__ = "knowledge_categories"
    __table_args__ = (
        CheckConstraint(
            "status in ('active', 'hidden', 'archived')",
            name="ck_knowledge_categories_status",
        ),
        CheckConstraint("id != parent_id", name="ck_knowledge_categories_not_self_parent"),
        CheckConstraint("sort_order >= 0", name="ck_knowledge_categories_sort_order"),
        Index("ix_knowledge_categories_parent_id", "parent_id"),
        Index("ix_knowledge_categories_path", "path", unique=True),
        Index("ix_knowledge_categories_status", "status"),
        Index("ix_knowledge_categories_parent_sort", "parent_id", "sort_order"),
        Index("ix_knowledge_categories_parent_slug", "parent_id", "slug", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_categories.id", ondelete="RESTRICT"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(CATEGORY_NAME_MAX_LENGTH), nullable=False)
    slug: Mapped[str] = mapped_column(String(CATEGORY_SLUG_MAX_LENGTH), nullable=False)
    path: Mapped[str] = mapped_column(String(CATEGORY_PATH_MAX_LENGTH), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=KnowledgeCategoryStatus.ACTIVE.value,
    )

    parent: Mapped[KnowledgeCategory | None] = relationship(
        back_populates="children",
        remote_side="KnowledgeCategory.id",
    )
    children: Mapped[list[KnowledgeCategory]] = relationship(
        back_populates="parent",
        cascade="save-update, merge",
        order_by="(KnowledgeCategory.sort_order, KnowledgeCategory.id)",
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
        return validate_category_name(name)

    @validates("slug")
    def _validate_slug(self, _: str, slug: str) -> str:
        return validate_category_slug(slug)

    @validates("status")
    def _validate_status(self, _: str, status: str) -> str:
        return KnowledgeCategoryStatus(status).value

    @validates("parent")
    def _validate_parent(
        self,
        _: str,
        parent: KnowledgeCategory | None,
    ) -> KnowledgeCategory | None:
        if would_create_category_cycle(self, parent):
            raise ValueError("分类不能移动到自身或自己的后代分类下")
        return parent


def normalize_category_name(name: str) -> str:
    """Normalize a category display name."""
    return name.strip()


def validate_category_name(name: str) -> str:
    """Validate and return a normalized category display name."""
    normalized = normalize_category_name(name)
    if not normalized:
        raise ValueError("分类名称不能为空")
    if len(normalized) > CATEGORY_NAME_MAX_LENGTH:
        raise ValueError(f"分类名称不能超过 {CATEGORY_NAME_MAX_LENGTH} 个字符")
    if "/" in normalized:
        raise ValueError("分类名称不能包含 /")
    if any(unicodedata.category(char).startswith("C") for char in normalized):
        raise ValueError("分类名称不能包含控制字符")
    return normalized


def validate_category_slug(slug: str) -> str:
    """Validate and return a normalized category slug."""
    normalized = slug.strip().lower()
    if not _SLUG_PATTERN.fullmatch(normalized):
        raise ValueError("分类标识只能包含小写字母、数字和中划线, 且不能以中划线开头或结尾")
    return normalized


def build_category_path(slug: str, parent_path: str | None = None) -> str:
    """Build the stable category path from a slug and optional parent path."""
    normalized_slug = validate_category_slug(slug)
    if parent_path:
        normalized_parent_path = parent_path.strip("/")
        return f"{normalized_parent_path}/{normalized_slug}"
    return normalized_slug


def would_create_category_cycle(
    category: KnowledgeCategory,
    new_parent: KnowledgeCategory | None,
) -> bool:
    """Return whether assigning ``new_parent`` would create a parent-child cycle."""
    if new_parent is None:
        return False
    if category.id is not None and new_parent.id == category.id:
        return True
    if category.path and new_parent.path:
        return new_parent.path == category.path or new_parent.path.startswith(f"{category.path}/")

    current = new_parent
    while current is not None:
        if current is category:
            return True
        if category.id is not None and current.id == category.id:
            return True
        current = current.parent
    return False
