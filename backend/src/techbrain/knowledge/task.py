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
from techbrain.models import (
    KnowledgeSyncFailureRecord,
    KnowledgeSyncTask,
    KnowledgeSyncTaskStatus,
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
    task_id: int | None = None

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
    record_task: bool = True,
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
    result = KnowledgeFullSyncResult(
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
    if record_task:
        task = record_full_sync_result(session, result)
        result = _with_task_id(result, task.id)

    session.commit()

    return result


def record_full_sync_result(
    session: Session,
    result: KnowledgeFullSyncResult,
) -> KnowledgeSyncTask:
    """Persist a full synchronization result and its failure details."""
    task = KnowledgeSyncTask(
        status=_task_status(result).value,
        started_at=result.started_at,
        finished_at=result.finished_at,
        scanned_count=result.scanned_count,
        success_count=result.success_count,
        failed_count=result.failed_count,
        created_count=result.created_count,
        updated_count=result.updated_count,
        restored_count=result.restored_count,
        unchanged_count=result.unchanged_count,
        deleted_count=result.deleted_count,
        failures=[
            KnowledgeSyncFailureRecord(
                path=failure.path,
                stage=failure.stage,
                code=failure.code,
                message=failure.message,
                field=failure.field,
                line=failure.line,
                column=failure.column,
            )
            for failure in result.failures
        ],
    )
    session.add(task)
    session.flush()
    return task


def list_sync_tasks_statement():
    """Return the base query for synchronization task history."""
    from sqlalchemy import select

    return select(KnowledgeSyncTask).order_by(KnowledgeSyncTask.started_at.desc())


def get_sync_task_statement(task_id: int):
    """Return the query for one synchronization task by ID."""
    from sqlalchemy import select

    return select(KnowledgeSyncTask).where(KnowledgeSyncTask.id == task_id)


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


def _task_status(result: KnowledgeFullSyncResult) -> KnowledgeSyncTaskStatus:
    if result.failed_count == 0:
        return KnowledgeSyncTaskStatus.SUCCESS
    if result.success_count > 0 or result.deleted_count > 0:
        return KnowledgeSyncTaskStatus.PARTIAL_SUCCESS
    return KnowledgeSyncTaskStatus.FAILED


def _with_task_id(result: KnowledgeFullSyncResult, task_id: int) -> KnowledgeFullSyncResult:
    return KnowledgeFullSyncResult(
        started_at=result.started_at,
        finished_at=result.finished_at,
        scanned_count=result.scanned_count,
        created_count=result.created_count,
        updated_count=result.updated_count,
        restored_count=result.restored_count,
        unchanged_count=result.unchanged_count,
        deleted_count=result.deleted_count,
        failed_count=result.failed_count,
        failures=result.failures,
        task_id=task_id,
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
