"""Knowledge tag and document-tag association model tests."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import (
    KnowledgeDocument,
    KnowledgeTag,
    KnowledgeTagStatus,
    knowledge_document_tags,
    normalize_tag_name,
    validate_tag_name,
)


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _write_markdown(root: Path) -> MarkdownFile:
    path = root / "backend/python/tag-model.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
schema_version: 1
id: tag-model-document
title: 标签模型文档
category: backend/python
tags:
  - ORM
  - 性能优化
created_at: 2026-06-29T10:00:00+08:00
updated_at: 2026-06-29T10:00:00+08:00
---

# 标签模型文档
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path="backend/python/tag-model.md",
        size_bytes=path.stat().st_size,
    )


def test_tag_name_normalization_is_case_unicode_and_whitespace_insensitive() -> None:
    assert normalize_tag_name("  \uff2f\uff32\uff2d  ") == "orm"
    assert normalize_tag_name("性能   优化") == "性能 优化"
    assert validate_tag_name("  性能   优化  ") == "性能 优化"


@pytest.mark.parametrize("name", ["", "   ", "line\nbreak", "a" * 81])
def test_tag_name_validation_rejects_invalid_values(name: str) -> None:
    with pytest.raises(ValueError):
        validate_tag_name(name)


def test_normalized_tag_name_is_unique() -> None:
    with _create_session() as session:
        session.add(
            KnowledgeTag(
                name="ORM",
                status=KnowledgeTagStatus.ACTIVE.value,
            )
        )
        session.commit()

        duplicate = KnowledgeTag(
            name="\uff4f\uff52\uff4d",
            status=KnowledgeTagStatus.ACTIVE.value,
        )
        session.add(duplicate)

        with pytest.raises(IntegrityError):
            session.commit()


def test_document_can_link_multiple_structured_tags() -> None:
    markdown_file = _write_markdown(Path(".pytest_tmp") / "tag_model_association")

    with _create_session() as session:
        sync_result = sync_markdown_document(session, markdown_file)
        assert sync_result.document is not None
        orm = KnowledgeTag(name="ORM", status=KnowledgeTagStatus.ACTIVE.value)
        performance = KnowledgeTag(name="性能优化", status=KnowledgeTagStatus.ACTIVE.value)
        sync_result.document.tag_nodes.extend((orm, performance))
        session.commit()

        document = session.scalar(
            select(KnowledgeDocument).where(KnowledgeDocument.document_id == "tag-model-document")
        )
        association_count = session.scalar(
            select(func.count()).select_from(knowledge_document_tags)
        )

        assert document is not None
        assert document.tags == ["ORM", "性能优化"]
        assert [tag.normalized_name for tag in document.tag_nodes] == ["orm", "性能优化"]
        assert association_count == 2
        assert orm.documents == [document]
        assert performance.documents == [document]
