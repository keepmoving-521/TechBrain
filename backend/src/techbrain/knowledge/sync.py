"""Knowledge document synchronization services."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from techbrain.knowledge.category_sync import CategoryPathError, sync_category_path
from techbrain.knowledge.parser import (
    MarkdownParseIssue,
    ParsedMarkdownDocument,
    parse_markdown_file,
)
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.models import DocumentSyncStatus, KnowledgeCategory, KnowledgeDocument


@dataclass(frozen=True)
class NewDocumentSyncResult:
    """Result of syncing one newly discovered Markdown document."""

    status: Literal["created", "updated", "restored", "unchanged", "skipped", "error"]
    document: KnowledgeDocument | None
    errors: tuple[MarkdownParseIssue, ...] = ()


@dataclass(frozen=True)
class DeletedDocumentSyncResult:
    """Result of marking missing source documents as deleted."""

    deleted_count: int
    deleted_documents: tuple[KnowledgeDocument, ...]


def sync_new_markdown_document(
    session: Session,
    markdown_file: MarkdownFile,
    *,
    encoding: str = "utf-8",
    scanned_at: datetime | None = None,
) -> NewDocumentSyncResult:
    """Insert a first-seen Markdown document into structured storage.

    This compatibility wrapper keeps V10-007 behavior: existing documents are not updated.
    Use `sync_markdown_document` when existing documents should be updated.
    """
    parse_result = parse_markdown_file(markdown_file, encoding=encoding)
    if parse_result.status == "error" or parse_result.document is None:
        return NewDocumentSyncResult(
            status="error",
            document=None,
            errors=parse_result.errors,
        )

    parsed_document = parse_result.document
    existing = _find_document_by_id(session, parsed_document) or _find_document_by_path(
        session,
        parsed_document,
    )
    if existing is not None:
        return NewDocumentSyncResult(status="skipped", document=existing)

    now = scanned_at or datetime.now(UTC)
    category_result = _resolve_category(session, parsed_document)
    if isinstance(category_result, MarkdownParseIssue):
        return NewDocumentSyncResult(status="error", document=None, errors=(category_result,))
    document = _build_knowledge_document(
        parsed_document,
        category=category_result,
        scanned_at=now,
    )
    session.add(document)
    session.flush()

    return NewDocumentSyncResult(status="created", document=document)


def sync_markdown_document(
    session: Session,
    markdown_file: MarkdownFile,
    *,
    encoding: str = "utf-8",
    scanned_at: datetime | None = None,
) -> NewDocumentSyncResult:
    """Create or update one Markdown document in structured storage."""
    parse_result = parse_markdown_file(markdown_file, encoding=encoding)
    if parse_result.status == "error" or parse_result.document is None:
        return NewDocumentSyncResult(
            status="error",
            document=None,
            errors=parse_result.errors,
        )

    parsed_document = parse_result.document
    existing = _find_document_by_id(session, parsed_document)
    now = scanned_at or datetime.now(UTC)

    if existing is None:
        path_conflict = _find_document_by_path(session, parsed_document)
        if path_conflict is not None:
            return NewDocumentSyncResult(
                status="error",
                document=path_conflict,
                errors=(
                    _sync_error(
                        parsed_document,
                        "DOCUMENT_PATH_CONFLICT",
                        "当前路径已被另一篇文档占用",
                        field="relative_path",
                    ),
                ),
            )
        category_result = _resolve_category(session, parsed_document)
        if isinstance(category_result, MarkdownParseIssue):
            return NewDocumentSyncResult(status="error", document=None, errors=(category_result,))
        document = _build_knowledge_document(
            parsed_document,
            category=category_result,
            scanned_at=now,
        )
        session.add(document)
        session.flush()
        return NewDocumentSyncResult(status="created", document=document)

    values = _document_values(parsed_document)
    path_conflict = _find_document_by_path(session, parsed_document)
    if path_conflict is not None and path_conflict.id != existing.id:
        return NewDocumentSyncResult(
            status="error",
            document=existing,
            errors=(
                _sync_error(
                    parsed_document,
                    "DOCUMENT_PATH_CONFLICT",
                    "移动后的路径已被另一篇文档占用",
                    field="relative_path",
                ),
            ),
        )

    category_result = _resolve_category(session, parsed_document)
    if isinstance(category_result, MarkdownParseIssue):
        return NewDocumentSyncResult(
            status="error",
            document=existing,
            errors=(category_result,),
        )

    if existing.is_deleted:
        _apply_document_values(existing, values)
        existing.category_node = category_result
        existing.sync_status = DocumentSyncStatus.SYNCED.value
        existing.sync_error = None
        existing.last_scanned_at = now
        existing.last_synced_at = now
        existing.is_deleted = False
        existing.deleted_at = None
        session.flush()
        return NewDocumentSyncResult(status="restored", document=existing)

    if _document_hashes_unchanged(existing, values) and existing.category_id == category_result.id:
        return NewDocumentSyncResult(status="unchanged", document=existing)

    _apply_document_values(existing, values)
    existing.category_node = category_result
    existing.sync_status = DocumentSyncStatus.SYNCED.value
    existing.sync_error = None
    existing.last_scanned_at = now
    existing.last_synced_at = now
    existing.is_deleted = False
    existing.deleted_at = None
    session.flush()

    return NewDocumentSyncResult(status="updated", document=existing)


def mark_missing_documents_deleted(
    session: Session,
    scanned_files: tuple[MarkdownFile, ...],
    *,
    deleted_at: datetime | None = None,
) -> DeletedDocumentSyncResult:
    """Soft-delete active documents whose source paths were not found in this scan."""
    scanned_paths = {file.relative_path for file in scanned_files}
    now = deleted_at or datetime.now(UTC)
    candidates = session.scalars(
        active_knowledge_documents_statement().where(
            KnowledgeDocument.relative_path.not_in(scanned_paths),
        )
    ).all()

    for document in candidates:
        document.is_deleted = True
        document.deleted_at = now
        document.sync_status = DocumentSyncStatus.DELETED.value
        document.sync_error = None
        document.last_scanned_at = now

    if candidates:
        session.flush()

    return DeletedDocumentSyncResult(
        deleted_count=len(candidates),
        deleted_documents=tuple(candidates),
    )


def active_knowledge_documents_statement():
    """Return the base query for normal lists and search indexing."""
    return select(KnowledgeDocument).where(KnowledgeDocument.is_deleted.is_(False))


def _find_document_by_id(
    session: Session,
    parsed_document: ParsedMarkdownDocument,
) -> KnowledgeDocument | None:
    return session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.document_id == parsed_document.front_matter.id,
        )
    )


def _find_document_by_path(
    session: Session,
    parsed_document: ParsedMarkdownDocument,
) -> KnowledgeDocument | None:
    return session.scalar(
        select(KnowledgeDocument).where(
            KnowledgeDocument.relative_path == parsed_document.file.relative_path,
        )
    )


def _build_knowledge_document(
    parsed_document: ParsedMarkdownDocument,
    *,
    category: KnowledgeCategory,
    scanned_at: datetime,
) -> KnowledgeDocument:
    values = _document_values(parsed_document)
    return KnowledgeDocument(
        **values,
        category_node=category,
        sync_status=DocumentSyncStatus.SYNCED.value,
        sync_error=None,
        last_scanned_at=scanned_at,
        last_synced_at=scanned_at,
        is_deleted=False,
        deleted_at=None,
    )


def _resolve_category(
    session: Session,
    parsed_document: ParsedMarkdownDocument,
) -> KnowledgeCategory | MarkdownParseIssue:
    try:
        return sync_category_path(session, parsed_document.front_matter.category)
    except CategoryPathError as exc:
        return _sync_error(
            parsed_document,
            "CATEGORY_INVALID_PATH",
            str(exc),
            field="category",
        )


def _document_values(parsed_document: ParsedMarkdownDocument) -> dict[str, object]:
    front_matter = parsed_document.front_matter
    body = parsed_document.body
    content_hash, front_matter_hash = calculate_parsed_document_hashes(parsed_document)
    return {
        "document_id": front_matter.id,
        "title": front_matter.title,
        "category": front_matter.category,
        "summary": front_matter.summary,
        "body": body,
        "status": front_matter.status,
        "visibility": front_matter.visibility,
        "language": front_matter.language,
        "relative_path": parsed_document.file.relative_path,
        "absolute_path": str(parsed_document.file.path),
        "path_hash": _hash_text(parsed_document.file.relative_path),
        "content_hash": content_hash,
        "front_matter_hash": front_matter_hash,
        "tags": list(front_matter.tags),
        "aliases": list(front_matter.aliases),
        "source": _source_to_dict(front_matter.source),
        "source_created_at": front_matter.created_at,
        "source_updated_at": front_matter.updated_at,
    }


def calculate_parsed_document_hashes(
    parsed_document: ParsedMarkdownDocument,
) -> tuple[str, str]:
    """Return the body and semantic Front Matter hashes for optimistic writes."""
    return (
        _hash_text(parsed_document.body),
        _hash_text(_front_matter_fingerprint(parsed_document)),
    )


def _document_hashes_unchanged(
    document: KnowledgeDocument,
    values: dict[str, object],
) -> bool:
    return (
        document.path_hash == values["path_hash"]
        and document.content_hash == values["content_hash"]
        and document.front_matter_hash == values["front_matter_hash"]
    )


def _apply_document_values(document: KnowledgeDocument, values: dict[str, object]) -> None:
    for key, value in values.items():
        setattr(document, key, value)


def _source_to_dict(source) -> dict[str, object]:
    data = asdict(source)
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in data.items()
        if value is not None
    }


def _front_matter_fingerprint(parsed_document: ParsedMarkdownDocument) -> str:
    front_matter = parsed_document.front_matter
    return "|".join(
        (
            str(front_matter.schema_version),
            front_matter.id,
            front_matter.title,
            front_matter.category,
            ",".join(front_matter.tags),
            front_matter.status,
            front_matter.created_at.isoformat(),
            front_matter.updated_at.isoformat(),
            front_matter.summary or "",
            str(_source_to_dict(front_matter.source)),
            ",".join(front_matter.aliases),
            front_matter.language,
            front_matter.visibility,
        )
    )


def _hash_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _sync_error(
    parsed_document: ParsedMarkdownDocument,
    code: str,
    message: str,
    *,
    field: str | None = None,
) -> MarkdownParseIssue:
    return MarkdownParseIssue(
        file_path=parsed_document.file.relative_path,
        code=code,
        message=message,
        field=field,
    )
