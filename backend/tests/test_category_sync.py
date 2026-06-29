"""Markdown category path synchronization tests."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.knowledge.category_sync import (
    CategoryPathError,
    parse_category_path,
    sync_category_path,
)
from techbrain.models import KnowledgeCategory


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_parse_category_path_returns_ordered_canonical_segments() -> None:
    parsed = parse_category_path("backend/python/web-api")

    assert parsed.path == "backend/python/web-api"
    assert parsed.segments == ("backend", "python", "web-api")


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("", "不能为空"),
        (" backend/python", "首尾空白"),
        ("/backend/python", "不能以 / 开头或结尾"),
        ("backend//python", "第 2 段不能为空"),
        ("backend/assets", "保留目录"),
        ("Backend/python", "规范化小写标识"),
        ("backend/python_ai", "只能包含小写字母"),
        ("a" * 81, "只能包含小写字母"),
    ],
)
def test_parse_category_path_rejects_invalid_paths(path: str, message: str) -> None:
    with pytest.raises(CategoryPathError, match=message):
        parse_category_path(path)


def test_sync_category_path_reuses_existing_nodes() -> None:
    with _create_session() as session:
        first = sync_category_path(session, "backend/python")
        second = sync_category_path(session, "backend/python")
        session.commit()

        categories = session.scalars(select(KnowledgeCategory)).all()

        assert second.id == first.id
        assert len(categories) == 2


def test_sync_category_path_rejects_inconsistent_existing_tree() -> None:
    with _create_session() as session:
        backend = KnowledgeCategory(
            name="backend", slug="backend", path="backend", sort_order=0, status="active"
        )
        database = KnowledgeCategory(
            name="database", slug="database", path="database", sort_order=0, status="active"
        )
        inconsistent = KnowledgeCategory(
            parent=database,
            name="python",
            slug="python",
            path="backend/python",
            sort_order=0,
            status="active",
        )
        session.add_all((backend, database, inconsistent))
        session.commit()

        with pytest.raises(CategoryPathError, match="父子关系与路径不一致"):
            sync_category_path(session, "backend/python")
