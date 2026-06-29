"""Synchronize Front Matter tags into structured document-tag relations."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from techbrain.models import (
    KnowledgeDocument,
    KnowledgeTag,
    KnowledgeTagStatus,
    normalize_tag_name,
    validate_tag_name,
)


class TagSyncError(ValueError):
    """Raised when Front Matter tags cannot be synchronized safely."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PreparedTag:
    """Validated tag display name and stable normalized key."""

    name: str
    normalized_name: str


def prepare_document_tags(tag_names: tuple[str, ...]) -> tuple[PreparedTag, ...]:
    """Validate tag names and reject duplicates after full normalization."""
    prepared: list[PreparedTag] = []
    seen: set[str] = set()
    for position, raw_name in enumerate(tag_names, start=1):
        try:
            display_name = validate_tag_name(raw_name)
        except ValueError as exc:
            raise TagSyncError(
                "TAG_INVALID_NAME",
                f"标签列表第 {position} 项不合法: {exc}",
            ) from exc
        normalized_name = normalize_tag_name(display_name)
        if normalized_name in seen:
            raise TagSyncError(
                "TAG_DUPLICATE_NORMALIZED_NAME",
                f"标签 {raw_name!r} 与同一文档中的其他标签规范化后重复",
            )
        seen.add(normalized_name)
        prepared.append(
            PreparedTag(
                name=display_name,
                normalized_name=normalized_name,
            )
        )
    return tuple(prepared)


def sync_document_tags(
    session: Session,
    document: KnowledgeDocument,
    prepared_tags: tuple[PreparedTag, ...],
) -> bool:
    """Replace a document's structured tags and return whether data changed."""
    normalized_names = [tag.normalized_name for tag in prepared_tags]
    existing_tags = (
        session.scalars(
            select(KnowledgeTag).where(KnowledgeTag.normalized_name.in_(normalized_names))
        ).all()
        if normalized_names
        else []
    )
    tags_by_name = {tag.normalized_name: tag for tag in existing_tags}
    resolved_tags: list[KnowledgeTag] = []
    status_changed = False

    for prepared in prepared_tags:
        tag = tags_by_name.get(prepared.normalized_name)
        if tag is None:
            tag = KnowledgeTag(
                name=prepared.name,
                status=KnowledgeTagStatus.ACTIVE.value,
            )
            session.add(tag)
            tags_by_name[prepared.normalized_name] = tag
        elif tag.status != KnowledgeTagStatus.ACTIVE.value:
            tag.status = KnowledgeTagStatus.ACTIVE.value
            status_changed = True
        resolved_tags.append(tag)

    current_names = {tag.normalized_name for tag in document.tag_nodes}
    desired_names = set(normalized_names)
    association_changed = current_names != desired_names
    if association_changed:
        document.tag_nodes = resolved_tags
    return association_changed or status_changed
