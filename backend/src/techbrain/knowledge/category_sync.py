"""Synchronize Markdown category paths into the category tree."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from techbrain.models import (
    KnowledgeCategory,
    KnowledgeCategoryStatus,
    build_category_path,
    validate_category_slug,
)

RESERVED_CATEGORY_PARTS = {"assets", "drafts", "archive"}


class CategoryPathError(ValueError):
    """Raised when a Markdown category path cannot be mapped to the category tree."""


@dataclass(frozen=True)
class ParsedCategoryPath:
    """Canonical category path and its ordered path segments."""

    path: str
    segments: tuple[str, ...]


def parse_category_path(category_path: str) -> ParsedCategoryPath:
    """Validate a Markdown category path without silently normalizing invalid input."""
    if not isinstance(category_path, str) or not category_path:
        raise CategoryPathError("分类路径不能为空")
    if category_path != category_path.strip():
        raise CategoryPathError("分类路径不能包含首尾空白")
    if category_path.startswith("/") or category_path.endswith("/"):
        raise CategoryPathError("分类路径不能以 / 开头或结尾")

    raw_segments = category_path.split("/")
    canonical_segments: list[str] = []
    for position, segment in enumerate(raw_segments, start=1):
        if not segment:
            raise CategoryPathError(f"分类路径第 {position} 段不能为空")
        if segment in RESERVED_CATEGORY_PARTS:
            raise CategoryPathError(f"分类路径不能使用保留目录: {segment}")
        try:
            canonical = validate_category_slug(segment)
        except ValueError as exc:
            raise CategoryPathError(f"分类路径第 {position} 段 {segment!r} 非法: {exc}") from exc
        if canonical != segment:
            raise CategoryPathError(
                f"分类路径第 {position} 段 {segment!r} 必须使用规范化小写标识 {canonical!r}"
            )
        canonical_segments.append(canonical)

    path = "/".join(canonical_segments)
    if len(path) > 512:
        raise CategoryPathError("分类路径不能超过 512 个字符")
    return ParsedCategoryPath(path=path, segments=tuple(canonical_segments))


def sync_category_path(session: Session, category_path: str) -> KnowledgeCategory:
    """Create missing category nodes and return the leaf category for a path."""
    parsed = parse_category_path(category_path)
    parent: KnowledgeCategory | None = None
    current_path: str | None = None

    for segment in parsed.segments:
        current_path = build_category_path(segment, current_path)
        category = session.scalar(
            select(KnowledgeCategory).where(KnowledgeCategory.path == current_path)
        )
        if category is None:
            category = KnowledgeCategory(
                parent=parent,
                name=segment,
                slug=segment,
                path=current_path,
                sort_order=0,
                status=KnowledgeCategoryStatus.ACTIVE.value,
            )
            session.add(category)
            session.flush()
        elif category.parent_id != (parent.id if parent else None):
            raise CategoryPathError(f"分类路径 {current_path!r} 的父子关系与路径不一致")
        parent = category

    if parent is None:  # pragma: no cover - guarded by parse_category_path
        raise CategoryPathError("分类路径不能为空")
    return parent
