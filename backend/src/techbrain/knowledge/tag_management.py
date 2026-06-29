"""Tag management with safe Markdown Front Matter write-back."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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
from techbrain.knowledge.tag_sync import TagSyncError, prepare_document_tags
from techbrain.models import (
    KnowledgeDocument,
    KnowledgeTag,
    KnowledgeTagStatus,
    knowledge_document_tags,
    normalize_tag_name,
    validate_tag_name,
)

_TOP_LEVEL_FIELD_PATTERN = re.compile(r"^(?P<field>tags|updated_at)\s*:")


class TagManagementError(RuntimeError):
    """Base tag management failure."""


class TagNotFoundError(TagManagementError):
    """Requested tag does not exist."""


class TagValidationError(TagManagementError):
    """Requested tag mutation violates naming rules."""


class TagConflictError(TagManagementError):
    """Requested tag mutation conflicts with current data or Markdown state."""


@dataclass(frozen=True)
class _TagMarkdownRewrite:
    document: KnowledgeDocument
    path: Path
    original_content: str
    updated_content: str


def create_tag(session: Session, name: str) -> KnowledgeTag:
    """Create one unused active tag with normalized-name conflict detection."""
    display_name = _validated_name(name)
    normalized_name = normalize_tag_name(display_name)
    _ensure_name_available(session, normalized_name)
    tag = KnowledgeTag(name=display_name, status=KnowledgeTagStatus.ACTIVE.value)
    session.add(tag)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise TagConflictError(f"标签规范化名称已存在: {normalized_name}") from exc
    return tag


def rename_tag(
    session: Session,
    settings: Settings,
    tag_id: int,
    name: str,
    *,
    changed_at: datetime | None = None,
) -> KnowledgeTag:
    """Rename a tag and safely replace it in every associated Markdown file."""
    tag = session.get(KnowledgeTag, tag_id)
    if tag is None:
        raise TagNotFoundError("标签不存在")
    display_name = _validated_name(name)
    normalized_name = normalize_tag_name(display_name)
    if tag.name == display_name:
        return tag
    _ensure_name_available(session, normalized_name, exclude_id=tag.id)

    documents = list(
        session.scalars(
            select(KnowledgeDocument)
            .join(
                knowledge_document_tags,
                knowledge_document_tags.c.document_id == KnowledgeDocument.id,
            )
            .where(knowledge_document_tags.c.tag_id == tag.id)
            .order_by(KnowledgeDocument.id)
        ).all()
    )
    if any(document.is_deleted for document in documents):
        raise TagConflictError("标签关联了源文件已删除的文档, 无法安全重命名")
    if not documents:
        tag.name = display_name
        session.commit()
        return tag

    operation_time = changed_at or datetime.now(UTC)
    rewrites = _prepare_rewrites(
        documents,
        settings,
        old_normalized_name=tag.normalized_name,
        new_display_name=display_name,
        changed_at=operation_time,
    )
    written: list[_TagMarkdownRewrite] = []
    try:
        tag.name = display_name
        session.flush()
        for rewrite in rewrites:
            _atomic_replace_if_unchanged(rewrite, settings.knowledge_file_encoding)
            written.append(rewrite)
        for rewrite in rewrites:
            result = sync_markdown_document(
                session,
                _markdown_file(rewrite.path, rewrite.document.relative_path),
                encoding=settings.knowledge_file_encoding,
                scanned_at=operation_time,
            )
            if result.status == "error":
                message = result.errors[0].message if result.errors else "文档重新同步失败"
                raise TagConflictError(message)
        session.commit()
    except TagManagementError:
        session.rollback()
        _restore_written_files(written, settings.knowledge_file_encoding)
        raise
    except (OSError, UnicodeError, SQLAlchemyError, ValueError) as exc:
        session.rollback()
        _restore_written_files(written, settings.knowledge_file_encoding)
        raise TagConflictError(f"标签重命名未完成: {exc}") from exc
    return tag


def delete_tag(session: Session, tag_id: int) -> None:
    """Delete a tag only when no document association exists."""
    tag = session.get(KnowledgeTag, tag_id)
    if tag is None:
        raise TagNotFoundError("标签不存在")
    document_exists = session.scalar(
        select(knowledge_document_tags.c.document_id)
        .where(knowledge_document_tags.c.tag_id == tag.id)
        .limit(1)
    )
    if document_exists is not None:
        raise TagConflictError("标签正在被文档使用, 无法直接删除")
    session.delete(tag)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise TagConflictError("标签已被其他数据引用, 无法删除") from exc


def _validated_name(name: str) -> str:
    try:
        return validate_tag_name(name)
    except ValueError as exc:
        raise TagValidationError(str(exc)) from exc


def _ensure_name_available(
    session: Session,
    normalized_name: str,
    *,
    exclude_id: int | None = None,
) -> None:
    statement = select(KnowledgeTag.id).where(KnowledgeTag.normalized_name == normalized_name)
    if exclude_id is not None:
        statement = statement.where(KnowledgeTag.id != exclude_id)
    if session.scalar(statement) is not None:
        raise TagConflictError(f"标签规范化名称已存在: {normalized_name}")


def _prepare_rewrites(
    documents: list[KnowledgeDocument],
    settings: Settings,
    *,
    old_normalized_name: str,
    new_display_name: str,
    changed_at: datetime,
) -> tuple[_TagMarkdownRewrite, ...]:
    try:
        config = build_knowledge_repository_config(settings)
    except KnowledgeConfigurationError as exc:
        raise TagValidationError(str(exc)) from exc

    rewrites: list[_TagMarkdownRewrite] = []
    for document in documents:
        path = Path(document.absolute_path).resolve()
        expected_path = (config.root / Path(document.relative_path)).resolve()
        if path != expected_path or not path.is_relative_to(config.root):
            raise TagConflictError(f"文档路径超出知识库或已变化: {document.relative_path}")
        try:
            original_content = path.read_text(encoding=config.file_encoding)
        except (OSError, UnicodeError) as exc:
            raise TagConflictError(f"无法读取文档: {document.relative_path}: {exc}") from exc

        parsed = _parse_for_write(document, path, original_content)
        updated_tags = _renamed_tags(
            parsed.front_matter.tags,
            old_normalized_name,
            new_display_name,
            document.relative_path,
        )
        try:
            prepare_document_tags(updated_tags)
        except TagSyncError as exc:
            raise TagConflictError(
                f"标签重命名会使文档标签冲突: {document.relative_path}: {exc}"
            ) from exc
        effective_time = max(changed_at, parsed.front_matter.updated_at)
        updated_content = _rewrite_front_matter_tags(
            original_content,
            tags=updated_tags,
            updated_at=effective_time,
        )
        result = parse_markdown_content(
            _markdown_file(path, document.relative_path),
            updated_content,
        )
        if result.status == "error" or result.document is None:
            message = result.errors[0].message if result.errors else "回写内容不合法"
            raise TagConflictError(f"文档回写校验失败: {document.relative_path}: {message}")
        rewrites.append(
            _TagMarkdownRewrite(
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
        raise TagConflictError(f"文档已无法安全解析: {document.relative_path}: {message}")
    parsed = result.document
    content_hash, front_matter_hash = calculate_parsed_document_hashes(parsed)
    if (
        parsed.front_matter.id != document.document_id
        or content_hash != document.content_hash
        or front_matter_hash != document.front_matter_hash
    ):
        raise TagConflictError(f"文档在同步后已被外部修改: {document.relative_path}")
    return parsed


def _renamed_tags(
    tags: tuple[str, ...],
    old_normalized_name: str,
    new_display_name: str,
    relative_path: str,
) -> tuple[str, ...]:
    matches = [
        index for index, name in enumerate(tags) if normalize_tag_name(name) == old_normalized_name
    ]
    if len(matches) != 1:
        raise TagConflictError(f"文档标签关联不一致: {relative_path}")
    updated = list(tags)
    updated[matches[0]] = new_display_name
    return tuple(updated)


def _rewrite_front_matter_tags(
    content: str,
    *,
    tags: tuple[str, ...],
    updated_at: datetime,
) -> str:
    lines = content.splitlines(keepends=True)
    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if not lines or lines[0].strip() != "---" or closing_index is None:
        raise TagConflictError("Front Matter 结构不完整, 无法安全回写")

    tag_indexes = _field_indexes(lines, closing_index, "tags")
    if len(tag_indexes) != 1:
        raise TagConflictError("Front Matter tags 字段缺失或重复")
    tag_index = tag_indexes[0]
    tag_end = tag_index + 1
    while tag_end < closing_index and (
        not lines[tag_end].strip() or lines[tag_end].startswith((" ", "\t"))
    ):
        tag_end += 1

    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    replacement = _serialized_tags(tags, newline)
    lines[tag_index:tag_end] = replacement

    closing_index = next(
        index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"
    )
    updated_indexes = _field_indexes(lines, closing_index, "updated_at")
    if len(updated_indexes) != 1:
        raise TagConflictError("Front Matter updated_at 字段缺失或重复")
    updated_index = updated_indexes[0]
    lines[updated_index] = f"updated_at: {updated_at.isoformat(timespec='seconds')}{newline}"
    return "".join(lines)


def _field_indexes(lines: list[str], closing_index: int, field_name: str) -> list[int]:
    indexes: list[int] = []
    for index in range(1, closing_index):
        match = _TOP_LEVEL_FIELD_PATTERN.match(lines[index])
        if match is not None and match.group("field") == field_name:
            indexes.append(index)
    return indexes


def _serialized_tags(tags: tuple[str, ...], newline: str) -> list[str]:
    if not tags:
        return [f"tags: []{newline}"]
    return [
        f"tags:{newline}",
        *(f"  - {_serialize_scalar(tag)}{newline}" for tag in tags),
    ]


def _serialize_scalar(value: str) -> str:
    if '"' not in value:
        return f'"{value}"'
    if "'" not in value:
        return f"'{value}'"
    raise TagConflictError("标签名称同时包含单双引号, 当前 Front Matter 格式无法安全回写")


def _atomic_replace_if_unchanged(rewrite: _TagMarkdownRewrite, encoding: str) -> None:
    current = rewrite.path.read_text(encoding=encoding)
    if current != rewrite.original_content:
        raise TagConflictError(f"文档在回写前发生并发修改: {rewrite.document.relative_path}")
    _atomic_write(rewrite.path, rewrite.updated_content, encoding)


def _restore_written_files(rewrites: list[_TagMarkdownRewrite], encoding: str) -> None:
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
        raise TagConflictError(f"标签变更失败且以下文件无法自动恢复: {', '.join(failures)}")


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
    return MarkdownFile(path=path, relative_path=relative_path, size_bytes=path.stat().st_size)
