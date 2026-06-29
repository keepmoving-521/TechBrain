"""Transactional category management with safe Markdown metadata write-back."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from techbrain.core.config import Settings
from techbrain.knowledge.config import (
    KnowledgeConfigurationError,
    build_knowledge_repository_config,
)
from techbrain.knowledge.parser import ParsedMarkdownDocument, parse_markdown_content
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import (
    calculate_parsed_document_hashes,
    sync_markdown_document,
)
from techbrain.models import (
    KnowledgeCategory,
    KnowledgeCategoryStatus,
    KnowledgeDocument,
    build_category_path,
    validate_category_name,
    validate_category_slug,
    would_create_category_cycle,
)

_UNSET: Final = object()
_TOP_LEVEL_FIELD_PATTERN = re.compile(r"^(?P<field>category|updated_at)\s*:")


class CategoryManagementError(RuntimeError):
    """Base category management failure."""


class CategoryNotFoundError(CategoryManagementError):
    """Requested category or parent does not exist."""


class CategoryValidationError(CategoryManagementError):
    """Requested category mutation violates domain rules."""


class CategoryConflictError(CategoryManagementError):
    """Requested mutation conflicts with current category or Markdown state."""


@dataclass(frozen=True)
class _MarkdownRewrite:
    document: KnowledgeDocument
    path: Path
    original_content: str
    updated_content: str


def create_category(
    session: Session,
    *,
    name: str,
    slug: str,
    parent_id: int | None = None,
    sort_order: int = 0,
) -> KnowledgeCategory:
    """Create one empty category after validating its parent and target path."""
    normalized_name = _validated_name(name)
    normalized_slug = _validated_slug(slug)
    if sort_order < 0:
        raise CategoryValidationError("分类排序值不能小于 0")

    parent = _get_parent(session, parent_id)
    path = build_category_path(normalized_slug, parent.path if parent else None)
    if len(path) > 512:
        raise CategoryValidationError("分类路径不能超过 512 个字符")
    _ensure_path_available(session, path)
    category = KnowledgeCategory(
        parent=parent,
        name=normalized_name,
        slug=normalized_slug,
        path=path,
        sort_order=sort_order,
        status=KnowledgeCategoryStatus.ACTIVE.value,
    )
    session.add(category)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise CategoryConflictError(f"分类路径已存在: {path}") from exc
    return category


def update_category(
    session: Session,
    settings: Settings,
    category_id: int,
    *,
    name: str | object = _UNSET,
    slug: str | object = _UNSET,
    parent_id: int | None | object = _UNSET,
    sort_order: int | object = _UNSET,
    changed_at: datetime | None = None,
) -> KnowledgeCategory:
    """Rename, move or reorder a category without violating Markdown SSOT."""
    if all(value is _UNSET for value in (name, slug, parent_id, sort_order)):
        raise CategoryValidationError("至少需要提供一个分类变更字段")

    category = session.get(KnowledgeCategory, category_id)
    if category is None:
        raise CategoryNotFoundError("分类不存在")

    desired_name = category.name if name is _UNSET else _validated_name(str(name))
    desired_slug = category.slug if slug is _UNSET else _validated_slug(str(slug))
    desired_sort_order = category.sort_order if sort_order is _UNSET else int(sort_order)
    if desired_sort_order < 0:
        raise CategoryValidationError("分类排序值不能小于 0")
    desired_parent = category.parent if parent_id is _UNSET else _get_parent(session, parent_id)
    if would_create_category_cycle(category, desired_parent):
        raise CategoryConflictError("分类不能移动到自身或自己的后代分类下")

    desired_path = build_category_path(
        desired_slug,
        desired_parent.path if desired_parent else None,
    )
    path_changed = desired_path != category.path
    subtree = _load_subtree(session, category.path)
    path_mapping = _build_path_mapping(category.path, desired_path, subtree)
    if path_changed:
        _ensure_subtree_paths_available(session, subtree, path_mapping)

    rewrites: tuple[_MarkdownRewrite, ...] = ()
    if path_changed:
        documents = session.scalars(
            select(KnowledgeDocument).where(
                KnowledgeDocument.category_id.in_([item.id for item in subtree])
            )
        ).all()
        if any(document.is_deleted for document in documents):
            raise CategoryConflictError("分类或其子分类包含源文件已删除的文档, 无法安全回写")
        rewrites = _prepare_markdown_rewrites(
            documents,
            path_mapping,
            settings,
            changed_at=changed_at or datetime.now(UTC),
        )

    written: list[_MarkdownRewrite] = []
    try:
        category.name = desired_name
        category.slug = desired_slug
        category.parent = desired_parent
        category.sort_order = desired_sort_order
        for item in subtree:
            item.path = path_mapping[item.path]
        session.flush()

        for rewrite in rewrites:
            _atomic_replace_if_unchanged(rewrite, settings.knowledge_file_encoding)
            written.append(rewrite)
        for rewrite in rewrites:
            result = sync_markdown_document(
                session,
                _markdown_file(rewrite.path, rewrite.document.relative_path),
                encoding=settings.knowledge_file_encoding,
                scanned_at=changed_at,
            )
            if result.status == "error":
                message = result.errors[0].message if result.errors else "文档重新同步失败"
                raise CategoryConflictError(message)
        session.commit()
    except CategoryManagementError:
        session.rollback()
        _restore_written_files(written, settings.knowledge_file_encoding)
        raise
    except (OSError, UnicodeError, SQLAlchemyError, ValueError) as exc:
        session.rollback()
        _restore_written_files(written, settings.knowledge_file_encoding)
        raise CategoryConflictError(f"分类变更未完成: {exc}") from exc
    return category


def _validated_name(name: str) -> str:
    try:
        return validate_category_name(name)
    except ValueError as exc:
        raise CategoryValidationError(str(exc)) from exc


def _validated_slug(slug: str) -> str:
    try:
        return validate_category_slug(slug)
    except ValueError as exc:
        raise CategoryValidationError(str(exc)) from exc


def _get_parent(session: Session, parent_id: int | None | object) -> KnowledgeCategory | None:
    if parent_id is None:
        return None
    if not isinstance(parent_id, int):
        raise CategoryValidationError("父分类 ID 不合法")
    parent = session.get(KnowledgeCategory, parent_id)
    if parent is None:
        raise CategoryNotFoundError("父分类不存在")
    return parent


def _ensure_path_available(session: Session, path: str) -> None:
    if session.scalar(select(KnowledgeCategory.id).where(KnowledgeCategory.path == path)):
        raise CategoryConflictError(f"分类路径已存在: {path}")


def _load_subtree(session: Session, root_path: str) -> list[KnowledgeCategory]:
    return list(
        session.scalars(
            select(KnowledgeCategory)
            .where(
                (KnowledgeCategory.path == root_path)
                | (KnowledgeCategory.path.like(f"{root_path}/%"))
            )
            .order_by(KnowledgeCategory.path)
        ).all()
    )


def _build_path_mapping(
    old_root: str,
    new_root: str,
    subtree: list[KnowledgeCategory],
) -> dict[str, str]:
    return {
        category.path: f"{new_root}{category.path.removeprefix(old_root)}" for category in subtree
    }


def _ensure_subtree_paths_available(
    session: Session,
    subtree: list[KnowledgeCategory],
    path_mapping: dict[str, str],
) -> None:
    new_paths = list(path_mapping.values())
    if any(len(path) > 512 for path in new_paths):
        raise CategoryValidationError("移动后的分类路径不能超过 512 个字符")
    subtree_ids = {category.id for category in subtree}
    conflict = session.scalar(
        select(KnowledgeCategory).where(
            KnowledgeCategory.path.in_(new_paths),
            KnowledgeCategory.id.not_in(subtree_ids),
        )
    )
    if conflict is not None:
        raise CategoryConflictError(f"目标分类路径已存在: {conflict.path}")


def _prepare_markdown_rewrites(
    documents: list[KnowledgeDocument],
    path_mapping: dict[str, str],
    settings: Settings,
    *,
    changed_at: datetime,
) -> tuple[_MarkdownRewrite, ...]:
    try:
        config = build_knowledge_repository_config(settings)
    except KnowledgeConfigurationError as exc:
        raise CategoryValidationError(str(exc)) from exc

    rewrites: list[_MarkdownRewrite] = []
    for document in documents:
        path = Path(document.absolute_path).resolve()
        expected_path = (config.root / Path(document.relative_path)).resolve()
        if path != expected_path or not path.is_relative_to(config.root):
            raise CategoryConflictError(f"文档路径超出知识库或已变化: {document.relative_path}")
        try:
            original_content = path.read_text(encoding=config.file_encoding)
        except (OSError, UnicodeError) as exc:
            raise CategoryConflictError(f"无法读取文档: {document.relative_path}: {exc}") from exc

        parsed = _parse_for_write(document, path, original_content)
        new_category = path_mapping.get(parsed.front_matter.category)
        if new_category is None:
            raise CategoryConflictError(f"文档分类关联不一致: {document.relative_path}")
        effective_time = max(changed_at, parsed.front_matter.updated_at)
        updated_content = _rewrite_front_matter(
            original_content,
            category=new_category,
            updated_at=effective_time,
        )
        updated_parsed = parse_markdown_content(
            _markdown_file(path, document.relative_path),
            updated_content,
        )
        if updated_parsed.status == "error" or updated_parsed.document is None:
            message = (
                updated_parsed.errors[0].message if updated_parsed.errors else "回写内容不合法"
            )
            raise CategoryConflictError(f"文档回写校验失败: {document.relative_path}: {message}")
        rewrites.append(
            _MarkdownRewrite(
                document=document,
                path=path,
                original_content=original_content,
                updated_content=updated_content,
            )
        )
    return tuple(rewrites)


def _parse_for_write(
    document: KnowledgeDocument,
    path: Path,
    content: str,
) -> ParsedMarkdownDocument:
    result = parse_markdown_content(_markdown_file(path, document.relative_path), content)
    if result.status == "error" or result.document is None:
        message = result.errors[0].message if result.errors else "文档解析失败"
        raise CategoryConflictError(f"文档已无法安全解析: {document.relative_path}: {message}")
    parsed = result.document
    content_hash, front_matter_hash = calculate_parsed_document_hashes(parsed)
    if (
        parsed.front_matter.id != document.document_id
        or parsed.front_matter.category != document.category
        or content_hash != document.content_hash
        or front_matter_hash != document.front_matter_hash
    ):
        raise CategoryConflictError(f"文档在同步后已被外部修改: {document.relative_path}")
    return parsed


def _rewrite_front_matter(
    content: str,
    *,
    category: str,
    updated_at: datetime,
) -> str:
    lines = content.splitlines(keepends=True)
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if not lines or lines[0].strip() != "---" or closing_index is None:
        raise CategoryConflictError("Front Matter 结构不完整, 无法安全回写")

    replacements = {
        "category": category,
        "updated_at": updated_at.isoformat(timespec="seconds"),
    }
    replaced: set[str] = set()
    for index in range(1, closing_index):
        match = _TOP_LEVEL_FIELD_PATTERN.match(lines[index])
        if match is None:
            continue
        field_name = match.group("field")
        if field_name in replaced:
            raise CategoryConflictError(f"Front Matter 字段重复: {field_name}")
        newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
        if not lines[index].endswith(("\n", "\r")):
            newline = ""
        lines[index] = f"{field_name}: {replacements[field_name]}{newline}"
        replaced.add(field_name)
    missing = replacements.keys() - replaced
    if missing:
        raise CategoryConflictError(f"Front Matter 缺少回写字段: {', '.join(sorted(missing))}")
    return "".join(lines)


def _atomic_replace_if_unchanged(rewrite: _MarkdownRewrite, encoding: str) -> None:
    current = rewrite.path.read_text(encoding=encoding)
    if current != rewrite.original_content:
        raise CategoryConflictError(f"文档在回写前发生并发修改: {rewrite.document.relative_path}")
    _atomic_write(rewrite.path, rewrite.updated_content, encoding)


def _restore_written_files(rewrites: list[_MarkdownRewrite], encoding: str) -> None:
    failures: list[str] = []
    for rewrite in reversed(rewrites):
        try:
            current = rewrite.path.read_text(encoding=encoding)
            if current != rewrite.updated_content:
                failures.append(rewrite.document.relative_path)
                continue
            _atomic_write(rewrite.path, rewrite.original_content, encoding)
        except (OSError, UnicodeError):
            failures.append(rewrite.document.relative_path)
    if failures:
        raise CategoryConflictError(f"分类变更失败且以下文件无法自动恢复: {', '.join(failures)}")


def _atomic_write(path: Path, content: str, encoding: str) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(content, encoding=encoding, newline="")
        os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _markdown_file(path: Path, relative_path: str) -> MarkdownFile:
    return MarkdownFile(
        path=path,
        relative_path=relative_path,
        size_bytes=path.stat().st_size,
    )
