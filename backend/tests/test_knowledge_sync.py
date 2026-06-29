"""Knowledge document synchronization tests."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import (
    active_knowledge_documents_statement,
    mark_missing_documents_deleted,
    sync_markdown_document,
    sync_new_markdown_document,
)
from techbrain.models import DocumentSyncStatus, KnowledgeCategory, KnowledgeDocument


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _write_markdown(
    root: Path,
    relative_path: str,
    document_id: str,
    *,
    title: str = "SQLAlchemy joinedload 使用指南",
    summary: str = "SQLAlchemy joinedload 的实践说明。",
    updated_at: str = "2026-06-25T10:30:00+08:00",
    body: str = "# SQLAlchemy joinedload 使用指南\n\n正文内容。",
    category: str = "backend/python",
) -> MarkdownFile:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {title}
category: {category}
tags:
  - orm
  - sqlalchemy
status: published
created_at: 2026-06-25T10:00:00+08:00
updated_at: {updated_at}
summary: {summary}
source:
  type: original
aliases:
  - joinedload
language: zh-CN
visibility: private
---

{body}
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
        assert saved.category_node.path == "backend/python"
        assert saved.category_id == saved.category_node.id
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


def test_sync_markdown_document_creates_and_reuses_category_tree() -> None:
    root = Path(".pytest_tmp") / "sync_category_tree"
    first_file = _write_markdown(root, "backend/python/first.md", "first-document")
    second_file = _write_markdown(root, "backend/python/second.md", "second-document")

    with _create_session() as session:
        first = sync_markdown_document(session, first_file)
        second = sync_markdown_document(session, second_file)
        session.commit()

        categories = session.scalars(
            select(KnowledgeCategory).order_by(KnowledgeCategory.path)
        ).all()

        assert [category.path for category in categories] == ["backend", "backend/python"]
        assert categories[1].parent_id == categories[0].id
        assert first.document is not None
        assert second.document is not None
        assert first.document.category_id == categories[1].id
        assert second.document.category_id == categories[1].id


def test_sync_markdown_document_updates_category_relationship() -> None:
    root = Path(".pytest_tmp") / "sync_category_change"
    markdown_file = _write_markdown(root, "backend/python/note.md", "category-note")

    with _create_session() as session:
        first = sync_markdown_document(session, markdown_file)
        session.commit()
        original_category_id = first.document.category_id if first.document else None

        changed_file = _write_markdown(
            root,
            "backend/python/note.md",
            "category-note",
            category="database/mysql",
            updated_at="2026-06-25T12:00:00+08:00",
        )
        second = sync_markdown_document(session, changed_file)
        session.commit()

        assert second.status == "updated"
        assert second.document is not None
        assert second.document.category == "database/mysql"
        assert second.document.category_node.path == "database/mysql"
        assert second.document.category_id != original_category_id


def test_sync_markdown_document_rejects_invalid_category_with_clear_error() -> None:
    root = Path(".pytest_tmp") / "sync_invalid_category"
    markdown_file = _write_markdown(
        root,
        "backend/python/invalid.md",
        "invalid-category",
        category="Backend/Python",
    )

    with _create_session() as session:
        result = sync_markdown_document(session, markdown_file)

        assert result.status == "error"
        assert result.errors[0].code == "FRONT_MATTER_INVALID_CATEGORY"
        assert result.errors[0].field == "category"
        assert "只能包含小写字母" in result.errors[0].message
        assert session.scalars(select(KnowledgeDocument)).all() == []
        assert session.scalars(select(KnowledgeCategory)).all() == []


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


def test_sync_markdown_document_returns_unchanged_without_mutating_timestamps() -> None:
    root = Path(".pytest_tmp") / "sync_unchanged"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )
    first_scanned_at = datetime(2026, 6, 25, 11, 0, tzinfo=UTC)
    second_scanned_at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)

    with _create_session() as session:
        first = sync_markdown_document(session, markdown_file, scanned_at=first_scanned_at)
        session.commit()

        original_content_hash = first.document.content_hash if first.document else None
        original_updated_at = first.document.updated_at if first.document else None
        second = sync_markdown_document(session, markdown_file, scanned_at=second_scanned_at)
        session.commit()

        assert first.status == "created"
        assert second.status == "unchanged"
        assert second.document is not None
        assert second.document.content_hash == original_content_hash
        assert second.document.last_scanned_at == first_scanned_at.replace(tzinfo=None)
        assert second.document.last_synced_at == first_scanned_at.replace(tzinfo=None)
        assert second.document.updated_at == original_updated_at


def test_sync_markdown_document_updates_changed_body() -> None:
    root = Path(".pytest_tmp") / "sync_changed_body"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )
    first_scanned_at = datetime(2026, 6, 25, 11, 0, tzinfo=UTC)
    second_scanned_at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)

    with _create_session() as session:
        first = sync_markdown_document(session, markdown_file, scanned_at=first_scanned_at)
        session.commit()

        original_content_hash = first.document.content_hash if first.document else None
        changed_file = _write_markdown(
            root,
            "backend/python/sqlalchemy-joinedload.md",
            "sqlalchemy-joinedload",
            updated_at="2026-06-25T11:30:00+08:00",
            body="# SQLAlchemy joinedload 使用指南\n\n更新后的正文内容。",
        )
        second = sync_markdown_document(session, changed_file, scanned_at=second_scanned_at)
        session.commit()

        count = len(session.scalars(select(KnowledgeDocument)).all())

        assert second.status == "updated"
        assert count == 1
        assert second.document is not None
        assert (
            second.document.body.strip() == "# SQLAlchemy joinedload 使用指南\n\n更新后的正文内容。"
        )
        assert second.document.content_hash != original_content_hash
        assert second.document.last_scanned_at == second_scanned_at.replace(tzinfo=None)
        assert second.document.last_synced_at == second_scanned_at.replace(tzinfo=None)


def test_sync_markdown_document_updates_changed_front_matter() -> None:
    root = Path(".pytest_tmp") / "sync_changed_front_matter"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )

    with _create_session() as session:
        first = sync_markdown_document(session, markdown_file)
        session.commit()

        original_front_matter_hash = first.document.front_matter_hash if first.document else None
        original_content_hash = first.document.content_hash if first.document else None
        changed_file = _write_markdown(
            root,
            "backend/python/sqlalchemy-joinedload.md",
            "sqlalchemy-joinedload",
            title="SQLAlchemy joinedload 深入实践",
            summary="更新后的摘要。",
            updated_at="2026-06-25T12:30:00+08:00",
        )
        second = sync_markdown_document(session, changed_file)
        session.commit()

        count = len(session.scalars(select(KnowledgeDocument)).all())

        assert second.status == "updated"
        assert count == 1
        assert second.document is not None
        assert second.document.title == "SQLAlchemy joinedload 深入实践"
        assert second.document.summary == "更新后的摘要。"
        assert second.document.front_matter_hash != original_front_matter_hash
        assert second.document.content_hash == original_content_hash


def test_sync_markdown_document_recognizes_file_move_by_document_id() -> None:
    root = Path(".pytest_tmp") / "sync_moved_file"
    original_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )
    moved_file = _write_markdown(
        root,
        "backend/sqlalchemy/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )
    second_scanned_at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)

    with _create_session() as session:
        first = sync_markdown_document(session, original_file)
        session.commit()

        original_database_id = first.document.id if first.document else None
        original_content_hash = first.document.content_hash if first.document else None
        original_front_matter_hash = first.document.front_matter_hash if first.document else None
        original_path_hash = first.document.path_hash if first.document else None
        result = sync_markdown_document(session, moved_file, scanned_at=second_scanned_at)
        session.commit()

        documents = session.scalars(select(KnowledgeDocument)).all()

        assert result.status == "updated"
        assert len(documents) == 1
        assert result.document is not None
        assert result.document.id == original_database_id
        assert result.document.document_id == "sqlalchemy-joinedload"
        assert result.document.relative_path == "backend/sqlalchemy/sqlalchemy-joinedload.md"
        assert result.document.absolute_path.replace("\\", "/").endswith(
            "backend/sqlalchemy/sqlalchemy-joinedload.md"
        )
        assert result.document.content_hash == original_content_hash
        assert result.document.front_matter_hash == original_front_matter_hash
        assert result.document.path_hash != original_path_hash
        assert result.document.last_scanned_at == second_scanned_at.replace(tzinfo=None)
        assert result.document.last_synced_at == second_scanned_at.replace(tzinfo=None)


def test_sync_markdown_document_rejects_move_to_occupied_path() -> None:
    root = Path(".pytest_tmp") / "sync_move_conflict"
    first_file = _write_markdown(root, "backend/python/first.md", "first-document")
    second_file = _write_markdown(root, "backend/python/second.md", "second-document")

    with _create_session() as session:
        sync_markdown_document(session, first_file)
        sync_markdown_document(session, second_file)
        session.commit()

        conflicting_move = _write_markdown(root, "backend/python/second.md", "first-document")
        result = sync_markdown_document(session, conflicting_move)
        session.commit()

        documents = session.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.document_id)
        ).all()

        assert result.status == "error"
        assert result.errors[0].code == "DOCUMENT_PATH_CONFLICT"
        assert len(documents) == 2
        assert documents[0].document_id == "first-document"
        assert documents[0].relative_path == "backend/python/first.md"
        assert documents[1].document_id == "second-document"
        assert documents[1].relative_path == "backend/python/second.md"


def test_mark_missing_documents_deleted_soft_deletes_absent_sources() -> None:
    root = Path(".pytest_tmp") / "sync_delete_missing"
    kept_file = _write_markdown(root, "backend/python/kept.md", "kept-document")
    missing_file = _write_markdown(root, "backend/python/missing.md", "missing-document")
    deleted_at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)

    with _create_session() as session:
        sync_markdown_document(session, kept_file)
        sync_markdown_document(session, missing_file)
        session.commit()

        result = mark_missing_documents_deleted(session, (kept_file,), deleted_at=deleted_at)
        session.commit()

        documents = session.scalars(
            select(KnowledgeDocument).order_by(KnowledgeDocument.document_id)
        ).all()
        active_documents = session.scalars(active_knowledge_documents_statement()).all()

        assert result.deleted_count == 1
        assert documents[0].document_id == "kept-document"
        assert documents[0].is_deleted is False
        assert documents[1].document_id == "missing-document"
        assert documents[1].is_deleted is True
        assert documents[1].deleted_at == deleted_at.replace(tzinfo=None)
        assert documents[1].sync_status == DocumentSyncStatus.DELETED.value
        assert [document.document_id for document in active_documents] == ["kept-document"]


def test_mark_missing_documents_deleted_is_idempotent_for_already_deleted_documents() -> None:
    root = Path(".pytest_tmp") / "sync_delete_idempotent"
    missing_file = _write_markdown(root, "backend/python/missing.md", "missing-document")

    with _create_session() as session:
        sync_markdown_document(session, missing_file)
        session.commit()

        first = mark_missing_documents_deleted(session, ())
        second = mark_missing_documents_deleted(session, ())
        session.commit()

        document = session.scalar(select(KnowledgeDocument))

        assert first.deleted_count == 1
        assert second.deleted_count == 0
        assert document is not None
        assert document.is_deleted is True
        assert document.sync_status == DocumentSyncStatus.DELETED.value


def test_sync_markdown_document_restores_soft_deleted_document_identity() -> None:
    root = Path(".pytest_tmp") / "sync_restore_deleted"
    markdown_file = _write_markdown(
        root,
        "backend/python/sqlalchemy-joinedload.md",
        "sqlalchemy-joinedload",
    )
    deleted_at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
    restored_at = datetime(2026, 6, 25, 14, 0, tzinfo=UTC)

    with _create_session() as session:
        created = sync_markdown_document(session, markdown_file)
        session.commit()

        original_database_id = created.document.id if created.document else None
        original_aliases = list(created.document.aliases) if created.document else []
        mark_missing_documents_deleted(session, (), deleted_at=deleted_at)
        session.commit()

        restored = sync_markdown_document(session, markdown_file, scanned_at=restored_at)
        session.commit()

        documents = session.scalars(select(KnowledgeDocument)).all()
        active_documents = session.scalars(active_knowledge_documents_statement()).all()

        assert restored.status == "restored"
        assert len(documents) == 1
        assert len(active_documents) == 1
        assert restored.document is not None
        assert restored.document.id == original_database_id
        assert restored.document.document_id == "sqlalchemy-joinedload"
        assert restored.document.aliases == original_aliases
        assert restored.document.is_deleted is False
        assert restored.document.deleted_at is None
        assert restored.document.sync_status == DocumentSyncStatus.SYNCED.value
        assert restored.document.last_scanned_at == restored_at.replace(tzinfo=None)
        assert restored.document.last_synced_at == restored_at.replace(tzinfo=None)
