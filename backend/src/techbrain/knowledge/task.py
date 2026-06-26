"""Full knowledge repository synchronization task."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from techbrain.knowledge.config import KnowledgeRepositoryConfig
from techbrain.knowledge.parser import MarkdownParseIssue
from techbrain.knowledge.scanner import MarkdownScanError, scan_markdown_files
from techbrain.knowledge.sync import (
    NewDocumentSyncResult,
    mark_missing_documents_deleted,
    sync_markdown_document,
)


@dataclass(frozen=True)
class KnowledgeSyncFailure:
    """A non-fatal full-sync failure item."""

    path: str
    stage: str
    code: str
    message: str
    field: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True)
class KnowledgeFullSyncResult:
    """Aggregated full synchronization result."""

    started_at: datetime
    finished_at: datetime
    scanned_count: int
    created_count: int = 0
    updated_count: int = 0
    restored_count: int = 0
    unchanged_count: int = 0
    deleted_count: int = 0
    failed_count: int = 0
    failures: tuple[KnowledgeSyncFailure, ...] = ()

    @property
    def success_count(self) -> int:
        """Return successfully handled Markdown file count."""
        return self.created_count + self.updated_count + self.restored_count + self.unchanged_count


@dataclass
class _SyncCounters:
    created: int = 0
    updated: int = 0
    restored: int = 0
    unchanged: int = 0
    failures: list[KnowledgeSyncFailure] = field(default_factory=list)


def run_full_knowledge_sync(
    session: Session,
    config: KnowledgeRepositoryConfig,
    *,
    started_at: datetime | None = None,
) -> KnowledgeFullSyncResult:
    """Scan a knowledge repository and synchronize all discovered Markdown files."""
    task_started_at = started_at or datetime.now(UTC)
    scan_result = scan_markdown_files(config)
    counters = _SyncCounters(
        failures=[_scan_error_to_failure(config.root, error) for error in scan_result.errors]
    )

    for markdown_file in scan_result.files:
        sync_result = sync_markdown_document(
            session,
            markdown_file,
            encoding=config.file_encoding,
            scanned_at=task_started_at,
        )
        _apply_sync_result(counters, sync_result)

    deleted_result = mark_missing_documents_deleted(
        session,
        scan_result.files,
        deleted_at=task_started_at,
    )
    session.commit()

    return KnowledgeFullSyncResult(
        started_at=task_started_at,
        finished_at=datetime.now(UTC),
        scanned_count=len(scan_result.files),
        created_count=counters.created,
        updated_count=counters.updated,
        restored_count=counters.restored,
        unchanged_count=counters.unchanged,
        deleted_count=deleted_result.deleted_count,
        failed_count=len(counters.failures),
        failures=tuple(counters.failures),
    )


def _apply_sync_result(counters: _SyncCounters, sync_result: NewDocumentSyncResult) -> None:
    if sync_result.status == "created":
        counters.created += 1
        return
    if sync_result.status == "updated":
        counters.updated += 1
        return
    if sync_result.status == "restored":
        counters.restored += 1
        return
    if sync_result.status in {"unchanged", "skipped"}:
        counters.unchanged += 1
        return

    counters.failures.extend(
        _parse_issue_to_failure(issue, stage="parse" if issue.code.startswith("FRONT_") else "sync")
        for issue in sync_result.errors
    )


def _scan_error_to_failure(root: Path, error: MarkdownScanError) -> KnowledgeSyncFailure:
    try:
        path = error.path.relative_to(root).as_posix()
    except ValueError:
        path = str(error.path)
    return KnowledgeSyncFailure(
        path=path,
        stage="scan",
        code=error.code,
        message=error.message,
    )


def _parse_issue_to_failure(issue: MarkdownParseIssue, *, stage: str) -> KnowledgeSyncFailure:
    return KnowledgeSyncFailure(
        path=issue.file_path,
        stage=stage,
        code=issue.code,
        message=issue.message,
        field=issue.field,
        line=issue.line,
        column=issue.column,
    )
