"""Knowledge document synchronization services."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from techbrain.knowledge.parser import (
    MarkdownParseIssue,
    ParsedMarkdownDocument,
    parse_markdown_file,
)
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.models import DocumentSyncStatus, KnowledgeDocument


@dataclass(frozen=True)
class NewDocumentSyncResult:
    """Result of syncing one newly discovered Markdown document."""

    status: Literal["created", "skipped", "error"]
    document: KnowledgeDocument | None
    errors: tuple[MarkdownParseIssue, ...] = ()


def sync_new_markdown_document(
    session: Session,
    markdown_file: MarkdownFile,
    *,
    encoding: str = "utf-8",
    scanned_at: datetime | None = None,
) -> NewDocumentSyncResult:
    """Insert a first-seen Markdown document into structured storage.

    This function is intentionally idempotent for V10-007. If a document with the same
    Front Matter ID or relative path already exists, it returns `skipped` and does not
    create a duplicate row. Update and move handling will be implemented by later sync
    requirements.
    """
    parse_result = parse_markdown_file(markdown_file, encoding=encoding)
    if parse_result.status == "error" or parse_result.document is None:
        return NewDocumentSyncResult(
            status="error",
            document=None,
            errors=parse_result.errors,
        )

    parsed_document = parse_result.document
    existing = _find_existing_document(session, parsed_document)
    if existing is not None:
        return NewDocumentSyncResult(status="skipped", document=existing)

    now = scanned_at or datetime.now(UTC)
    document = _build_knowledge_document(parsed_document, scanned_at=now)
    session.add(document)
    session.flush()

    return NewDocumentSyncResult(status="created", document=document)


def _find_existing_document(
    session: Session,
    parsed_document: ParsedMarkdownDocument,
) -> KnowledgeDocument | None:
    return session.scalar(
        select(KnowledgeDocument).where(
            or_(
                KnowledgeDocument.document_id == parsed_document.front_matter.id,
                KnowledgeDocument.relative_path == parsed_document.file.relative_path,
            )
        )
    )


def _build_knowledge_document(
    parsed_document: ParsedMarkdownDocument,
    *,
    scanned_at: datetime,
) -> KnowledgeDocument:
    front_matter = parsed_document.front_matter
    body = parsed_document.body

    return KnowledgeDocument(
        document_id=front_matter.id,
        title=front_matter.title,
        category=front_matter.category,
        summary=front_matter.summary,
        body=body,
        status=front_matter.status,
        visibility=front_matter.visibility,
        language=front_matter.language,
        relative_path=parsed_document.file.relative_path,
        absolute_path=str(parsed_document.file.path),
        path_hash=_hash_text(parsed_document.file.relative_path),
        content_hash=_hash_text(body),
        front_matter_hash=_hash_text(_front_matter_fingerprint(parsed_document)),
        tags=list(front_matter.tags),
        aliases=list(front_matter.aliases),
        source=_source_to_dict(front_matter.source),
        source_created_at=front_matter.created_at,
        source_updated_at=front_matter.updated_at,
        sync_status=DocumentSyncStatus.SYNCED.value,
        sync_error=None,
        last_scanned_at=scanned_at,
        last_synced_at=scanned_at,
        is_deleted=False,
        deleted_at=None,
    )


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
