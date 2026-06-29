"""Category management transaction and Markdown rollback tests."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import techbrain.knowledge.category_management as category_management
from techbrain.core.config import Environment, Settings
from techbrain.db.base import Base
from techbrain.knowledge.category_management import CategoryConflictError, update_category
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import KnowledgeCategory, KnowledgeDocument


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine, autoflush=False, expire_on_commit=False)


def _write_markdown(root: Path, file_name: str, document_id: str) -> MarkdownFile:
    path = root / "backend/python" / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {document_id}
category: backend/python
created_at: 2026-06-29T10:00:00+08:00
updated_at: 2026-06-29T10:00:00+08:00
---

# {document_id}
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path=f"backend/python/{file_name}",
        size_bytes=path.stat().st_size,
    )


def test_category_markdown_batch_failure_restores_files_and_database(monkeypatch) -> None:
    root = Path(".pytest_tmp") / "category_management_rollback"
    first_file = _write_markdown(root, "first.md", "rollback-first")
    second_file = _write_markdown(root, "second.md", "rollback-second")
    settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )

    with _create_session() as session:
        first = sync_markdown_document(session, first_file)
        sync_markdown_document(session, second_file)
        session.commit()
        assert first.document is not None
        category_id = first.document.category_id

        original_replace = category_management._atomic_replace_if_unchanged
        calls = 0

        def fail_on_second_write(rewrite, encoding: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise CategoryConflictError("模拟第二个文件回写失败")
            original_replace(rewrite, encoding)

        monkeypatch.setattr(
            category_management,
            "_atomic_replace_if_unchanged",
            fail_on_second_write,
        )

        with pytest.raises(CategoryConflictError, match="模拟第二个文件回写失败"):
            update_category(session, settings, category_id, slug="python3")

        category = session.get(KnowledgeCategory, category_id)
        document_categories = session.scalars(
            select(KnowledgeDocument.category).order_by(KnowledgeDocument.document_id)
        ).all()

        assert category is not None
        assert category.path == "backend/python"
        assert document_categories == ["backend/python", "backend/python"]
        assert "category: backend/python\n" in first_file.path.read_text(encoding="utf-8")
        assert "category: backend/python\n" in second_file.path.read_text(encoding="utf-8")
