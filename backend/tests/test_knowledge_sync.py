"""Knowledge document synchronization tests."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_new_markdown_document
from techbrain.models import DocumentSyncStatus, KnowledgeDocument


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _write_markdown(root: Path, relative_path: str, document_id: str) -> MarkdownFile:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: SQLAlchemy joinedload 使用指南
category: backend/python
tags:
  - orm
  - sqlalchemy
status: published
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
summary: SQLAlchemy joinedload 的实践说明。
source:
  type: original
aliases:
  - joinedload
language: zh-CN
visibility: private
---

# SQLAlchemy joinedload 使用指南

正文内容。
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path=relative_path,
        size_bytes=path.stat().st_size,
    )


def test_sync_new_markdown_document_creates_structured_record() -> None:
    root = Path(".pytest_tmp") / "sync_create"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )
    scanned_at = datetime(2026, 6, 25, 11, 0, tzinfo=UTC)

    with _create_session() as session:
        result = sync_new_markdown_document(session, markdown_file, scanned_at=scanned_at)
        session.commit()

        saved = session.scalar(select(KnowledgeDocument))

        assert result.status == "created"
        assert saved is not None
        assert saved.document_id == "sqlalchemy-joinedload"
        assert saved.title == "SQLAlchemy joinedload 使用指南"
        assert saved.category == "backend/python"
        assert saved.body.strip() == "# SQLAlchemy joinedload 使用指南\n\n正文内容。"
        assert saved.tags == ["orm", "sqlalchemy"]
        assert saved.aliases == ["joinedload"]
        assert saved.source == {"type": "original"}
        assert saved.relative_path == "backend/python/sqlalchemy-joinedload.md"
        assert saved.content_hash
        assert saved.front_matter_hash
        assert saved.path_hash
        assert saved.sync_status == DocumentSyncStatus.SYNCED.value
        assert saved.sync_error is None
        assert saved.last_scanned_at is not None
        assert saved.last_synced_at is not None
        assert saved.is_deleted is False


def test_sync_new_markdown_document_is_idempotent_by_document_id() -> None:
    root = Path(".pytest_tmp") / "sync_duplicate_id"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )

    with _create_session() as session:
        first = sync_new_markdown_document(session, markdown_file)
        second = sync_new_markdown_document(session, markdown_file)
        session.commit()

        count = len(session.scalars(select(KnowledgeDocument)).all())

        assert first.status == "created"
        assert second.status == "skipped"
        assert count == 1
        assert second.document is first.document


def test_sync_new_markdown_document_is_idempotent_by_relative_path() -> None:
    root = Path(".pytest_tmp") / "sync_duplicate_path"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )

    with _create_session() as session:
        first = sync_new_markdown_document(session, markdown_file)
        session.commit()

        path_duplicate = _write_markdown(
            root,
            "backend/python/sqlalchemy-joinedload.md",
            "another-document-id",
        )
        second = sync_new_markdown_document(session, path_duplicate)
        session.commit()

        count = len(session.scalars(select(KnowledgeDocument)).all())

        assert first.status == "created"
        assert second.status == "skipped"
        assert count == 1
        assert second.document is not None
        assert second.document.document_id == "sqlalchemy-joinedload"


def test_sync_new_markdown_document_returns_parse_errors_without_insert() -> None:
    root = Path(".pytest_tmp") / "sync_parse_error"
    path = root / "backend/python/broken.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Missing Front Matter", encoding="utf-8")
    markdown_file = MarkdownFile(
        path=path.resolve(),
        relative_path="backend/python/broken.md",
        size_bytes=path.stat().st_size,
    )

    with _create_session() as session:
        result = sync_new_markdown_document(session, markdown_file)
        count = len(session.scalars(select(KnowledgeDocument)).all())

        assert result.status == "error"
        assert result.document is None
        assert result.errors[0].code == "FRONT_MATTER_MISSING"
        assert count == 0
