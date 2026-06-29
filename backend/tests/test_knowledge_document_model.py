"""Knowledge document ORM model tests."""

from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.models import (
    DocumentSyncStatus,
    KnowledgeCategory,
    KnowledgeDocument,
    KnowledgeDocumentStatus,
)


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _document(**overrides) -> KnowledgeDocument:
    now = datetime(2026, 6, 25, 10, 0, tzinfo=UTC)
    backend = KnowledgeCategory(
        name="backend",
        slug="backend",
        path="backend",
        sort_order=0,
        status="active",
    )
    python = KnowledgeCategory(
        parent=backend,
        name="python",
        slug="python",
        path="backend/python",
        sort_order=0,
        status="active",
    )
    values = {
        "document_id": "sqlalchemy-joinedload",
        "title": "SQLAlchemy joinedload 使用指南",
        "category": "backend/python",
        "category_node": python,
        "summary": "SQLAlchemy joinedload 的实践说明。",
        "body": "# SQLAlchemy joinedload 使用指南\n",
        "status": KnowledgeDocumentStatus.PUBLISHED.value,
        "visibility": "private",
        "language": "zh-CN",
        "relative_path": "backend/python/sqlalchemy-joinedload.md",
        "absolute_path": "D:/Knowledge/backend/python/sqlalchemy-joinedload.md",
        "path_hash": "a" * 64,
        "content_hash": "b" * 64,
        "front_matter_hash": "c" * 64,
        "tags": ["orm", "sqlalchemy"],
        "aliases": ["joinedload"],
        "source": {"type": "original"},
        "source_created_at": now,
        "source_updated_at": now,
        "sync_status": DocumentSyncStatus.PENDING.value,
        "is_deleted": False,
    }
    values.update(overrides)
    return KnowledgeDocument(**values)


def test_knowledge_document_can_be_created_and_queried() -> None:
    with _create_session() as session:
        document = _document()
        session.add(document)
        session.commit()

        saved = session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.document_id == "sqlalchemy-joinedload"
            )
        )

        assert saved is not None
        assert saved.relative_path == "backend/python/sqlalchemy-joinedload.md"
        assert saved.tags == ["orm", "sqlalchemy"]
        assert saved.category_node.path == "backend/python"
        assert saved.sync_status == DocumentSyncStatus.PENDING.value


def test_knowledge_document_supports_content_update() -> None:
    with _create_session() as session:
        document = _document()
        session.add(document)
        session.commit()

        document.title = "SQLAlchemy joinedload 深入实践"
        document.content_hash = "d" * 64
        document.front_matter_hash = "e" * 64
        document.sync_status = DocumentSyncStatus.SYNCED.value
        document.last_synced_at = datetime(2026, 6, 25, 11, 0, tzinfo=UTC)
        session.commit()

        saved = session.get(KnowledgeDocument, document.id)

        assert saved is not None
        assert saved.title == "SQLAlchemy joinedload 深入实践"
        assert saved.content_hash == "d" * 64
        assert saved.sync_status == DocumentSyncStatus.SYNCED.value
        assert saved.last_synced_at is not None


def test_knowledge_document_supports_file_move_with_stable_document_id() -> None:
    with _create_session() as session:
        document = _document()
        session.add(document)
        session.commit()

        document.relative_path = "backend/sqlalchemy/sqlalchemy-joinedload.md"
        document.absolute_path = "D:/Knowledge/backend/sqlalchemy/sqlalchemy-joinedload.md"
        document.path_hash = "f" * 64
        session.commit()

        saved = session.scalar(
            select(KnowledgeDocument).where(
                KnowledgeDocument.document_id == "sqlalchemy-joinedload"
            )
        )

        assert saved is not None
        assert saved.document_id == "sqlalchemy-joinedload"
        assert saved.relative_path == "backend/sqlalchemy/sqlalchemy-joinedload.md"
        assert saved.path_hash == "f" * 64


def test_knowledge_document_supports_soft_delete() -> None:
    with _create_session() as session:
        deleted_at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
        document = _document()
        session.add(document)
        session.commit()

        document.is_deleted = True
        document.deleted_at = deleted_at
        document.sync_status = DocumentSyncStatus.DELETED.value
        session.commit()

        saved = session.get(KnowledgeDocument, document.id)

        assert saved is not None
        assert saved.is_deleted is True
        assert saved.deleted_at is not None
        assert saved.sync_status == DocumentSyncStatus.DELETED.value


def test_knowledge_document_records_sync_failure() -> None:
    with _create_session() as session:
        document = _document()
        session.add(document)
        session.commit()

        document.sync_status = DocumentSyncStatus.FAILED.value
        document.sync_error = "Front Matter 字段 updated_at 不符合规范"
        document.last_scanned_at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
        session.commit()

        saved = session.get(KnowledgeDocument, document.id)

        assert saved is not None
        assert saved.sync_status == DocumentSyncStatus.FAILED.value
        assert saved.sync_error == "Front Matter 字段 updated_at 不符合规范"
        assert saved.last_scanned_at is not None
