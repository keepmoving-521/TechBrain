"""Tag management transaction rollback tests."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import techbrain.knowledge.tag_management as tag_management
from techbrain.core.config import Environment, Settings
from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.knowledge.tag_management import TagConflictError, rename_tag
from techbrain.models import KnowledgeDocument, KnowledgeTag


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
tags:
  - orm
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


def test_tag_rename_batch_failure_restores_markdown_and_database(monkeypatch) -> None:
    root = Path(".pytest_tmp") / "tag_management_rollback"
    first_file = _write_markdown(root, "first.md", "tag-rollback-first")
    second_file = _write_markdown(root, "second.md", "tag-rollback-second")
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
        tag_id = first.document.tag_nodes[0].id

        original_replace = tag_management._atomic_replace_if_unchanged
        calls = 0

        def fail_on_second_write(rewrite, encoding: str) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise TagConflictError("模拟第二个标签文件回写失败")
            original_replace(rewrite, encoding)

        monkeypatch.setattr(
            tag_management,
            "_atomic_replace_if_unchanged",
            fail_on_second_write,
        )

        with pytest.raises(TagConflictError, match="模拟第二个标签文件回写失败"):
            rename_tag(session, settings, tag_id, "database-orm")

        tag = session.get(KnowledgeTag, tag_id)
        document_tags = session.scalars(
            select(KnowledgeDocument.tags).order_by(KnowledgeDocument.document_id)
        ).all()

        assert tag is not None
        assert tag.name == "orm"
        assert tag.normalized_name == "orm"
        assert document_tags == [["orm"], ["orm"]]
        assert "  - orm\n" in first_file.path.read_text(encoding="utf-8")
        assert "  - orm\n" in second_file.path.read_text(encoding="utf-8")
