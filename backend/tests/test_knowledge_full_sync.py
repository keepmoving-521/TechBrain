"""Full knowledge synchronization task tests."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.knowledge.config import KnowledgeRepositoryConfig
from techbrain.knowledge.task import run_full_knowledge_sync
from techbrain.models import DocumentSyncStatus, KnowledgeDocument


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _test_root(name: str) -> Path:
    root = Path(".pytest_tmp") / f"{name}_{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _config(root: Path) -> KnowledgeRepositoryConfig:
    return KnowledgeRepositoryConfig(
        root=root.resolve(),
        file_encoding="utf-8",
        ignore_file_name=".techbrainignore",
        ignore_patterns=(),
        include_drafts=False,
        include_archive=False,
        sync_batch_size=100,
        max_file_size_bytes=1024 * 1024,
    )


def _write_markdown(
    root: Path,
    relative_path: str,
    document_id: str,
    *,
    title: str = "SQLAlchemy joinedload 使用指南",
    body: str = "# SQLAlchemy joinedload 使用指南\n\n正文内容。",
    updated_at: str = "2026-06-25T10:30:00+08:00",
) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {title}
category: backend/python
tags:
  - orm
status: published
created_at: 2026-06-25T10:00:00+08:00
updated_at: {updated_at}
source:
  type: original
---

{body}
""",
        encoding="utf-8",
    )
    return path


def test_run_full_knowledge_sync_processes_repository_and_continues_after_failure() -> None:
    root = _test_root("full_sync_initial")
    _write_markdown(root, "backend/python/valid.md", "valid-document")
    broken = root / "backend/python/broken.md"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("# Missing Front Matter", encoding="utf-8")
    started_at = datetime(2026, 6, 25, 10, 0, tzinfo=UTC)

    with _create_session() as session:
        result = run_full_knowledge_sync(session, _config(root), started_at=started_at)

        documents = session.scalars(select(KnowledgeDocument)).all()

        assert result.scanned_count == 2
        assert result.created_count == 1
        assert result.failed_count == 1
        assert result.success_count == 1
        assert result.failures[0].path == "backend/python/broken.md"
        assert result.failures[0].code == "FRONT_MATTER_MISSING"
        assert len(documents) == 1
        assert documents[0].document_id == "valid-document"
        assert documents[0].sync_status == DocumentSyncStatus.SYNCED.value


def test_run_full_knowledge_sync_is_idempotent_when_files_do_not_change() -> None:
    root = _test_root("full_sync_idempotent")
    _write_markdown(root, "backend/python/valid.md", "valid-document")
    first_started_at = datetime(2026, 6, 25, 10, 0, tzinfo=UTC)
    second_started_at = datetime(2026, 6, 25, 11, 0, tzinfo=UTC)

    with _create_session() as session:
        first = run_full_knowledge_sync(session, _config(root), started_at=first_started_at)
        document = session.scalar(select(KnowledgeDocument))
        first_last_synced_at = document.last_synced_at if document else None

        second = run_full_knowledge_sync(session, _config(root), started_at=second_started_at)
        documents = session.scalars(select(KnowledgeDocument)).all()

        assert first.created_count == 1
        assert second.created_count == 0
        assert second.unchanged_count == 1
        assert len(documents) == 1
        assert documents[0].last_synced_at == first_last_synced_at


def test_run_full_knowledge_sync_handles_update_move_delete_and_restore() -> None:
    root = _test_root("full_sync_lifecycle")
    original_path = _write_markdown(root, "backend/python/valid.md", "valid-document")
    stale_path = _write_markdown(root, "backend/python/stale.md", "stale-document")

    with _create_session() as session:
        initial = run_full_knowledge_sync(session, _config(root))
        assert initial.created_count == 2

        original_path.unlink()
        _write_markdown(
            root,
            "backend/sqlalchemy/valid.md",
            "valid-document",
            title="SQLAlchemy joinedload 深入实践",
            body="# SQLAlchemy joinedload 深入实践\n\n移动并修改后的正文。",
            updated_at="2026-06-25T12:00:00+08:00",
        )
        stale_path.unlink()

        changed = run_full_knowledge_sync(session, _config(root))
        documents = session.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.document_id)
        ).all()

        assert changed.updated_count == 1
        assert changed.deleted_count == 1
        assert len(documents) == 2
        assert documents[0].document_id == "stale-document"
        assert documents[0].is_deleted is True
        assert documents[1].document_id == "valid-document"
        assert documents[1].is_deleted is False
        assert documents[1].relative_path == "backend/sqlalchemy/valid.md"
        assert documents[1].title == "SQLAlchemy joinedload 深入实践"

        _write_markdown(root, "backend/python/stale.md", "stale-document")
        restored = run_full_knowledge_sync(session, _config(root))
        restored_document = session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.document_id == "stale-document")
        )

        assert restored.restored_count == 1
        assert restored_document is not None
        assert restored_document.is_deleted is False
        assert restored_document.sync_status == DocumentSyncStatus.SYNCED.value
