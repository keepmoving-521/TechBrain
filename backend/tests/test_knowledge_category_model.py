"""Knowledge category ORM model tests."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from techbrain.db.base import Base
from techbrain.models import (
    KnowledgeCategory,
    KnowledgeCategoryStatus,
    build_category_path,
    validate_category_name,
    validate_category_slug,
    would_create_category_cycle,
)


def _create_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _category(
    *,
    name: str = "Python",
    slug: str = "python",
    parent: KnowledgeCategory | None = None,
    sort_order: int = 0,
    status: str = KnowledgeCategoryStatus.ACTIVE.value,
) -> KnowledgeCategory:
    return KnowledgeCategory(
        name=validate_category_name(name),
        slug=validate_category_slug(slug),
        path=build_category_path(slug, parent.path if parent else None),
        parent=parent,
        sort_order=sort_order,
        status=status,
    )


def test_knowledge_category_can_form_stable_tree_structure() -> None:
    with _create_session() as session:
        backend = _category(name="Backend", slug="backend", sort_order=20)
        python = _category(name="Python", slug="python", parent=backend, sort_order=10)
        sqlalchemy = _category(
            name="SQLAlchemy",
            slug="sqlalchemy",
            parent=python,
            sort_order=5,
        )
        session.add_all([backend, python, sqlalchemy])
        session.commit()

        saved = session.scalar(
            select(KnowledgeCategory).where(KnowledgeCategory.path == "backend/python/sqlalchemy")
        )

        assert saved is not None
        assert saved.parent is not None
        assert saved.parent.path == "backend/python"
        assert saved.path == "backend/python/sqlalchemy"
        assert [child.path for child in backend.children] == ["backend/python"]


def test_knowledge_category_sorts_siblings_by_sort_order() -> None:
    with _create_session() as session:
        root = _category(name="Backend", slug="backend")
        mysql = _category(name="MySQL", slug="mysql", parent=root, sort_order=20)
        python = _category(name="Python", slug="python", parent=root, sort_order=10)
        session.add_all([root, mysql, python])
        session.commit()
        session.refresh(root)

        assert [child.slug for child in root.children] == ["python", "mysql"]


def test_knowledge_category_rejects_duplicate_path() -> None:
    with _create_session() as session:
        session.add(_category(name="Python", slug="python"))
        session.add(_category(name="Python Duplicate", slug="python"))

        with pytest.raises(IntegrityError):
            session.commit()


def test_knowledge_category_rejects_self_parent_at_database_level() -> None:
    with _create_session() as session:
        category = _category(name="Python", slug="python")
        session.add(category)
        session.commit()

        category.parent_id = category.id

        with pytest.raises(IntegrityError):
            session.commit()


def test_would_create_category_cycle_detects_descendant_parent() -> None:
    with _create_session() as session:
        backend = _category(name="Backend", slug="backend")
        python = _category(name="Python", slug="python", parent=backend)
        sqlalchemy = _category(name="SQLAlchemy", slug="sqlalchemy", parent=python)
        session.add_all([backend, python, sqlalchemy])
        session.commit()

        assert would_create_category_cycle(backend, sqlalchemy) is True
        assert would_create_category_cycle(python, backend) is False
        assert would_create_category_cycle(python, python) is True

        with pytest.raises(ValueError):
            backend.parent = sqlalchemy


def test_category_name_rules_are_explicit() -> None:
    assert validate_category_name(" Python ") == "Python"

    for invalid_name in ["", "   ", "Backend/Python", "Python\nAI"]:
        with pytest.raises(ValueError):
            validate_category_name(invalid_name)

    with pytest.raises(ValueError):
        KnowledgeCategory(name="Backend/Python", slug="backend-python", path="backend-python")


def test_category_slug_rules_are_explicit() -> None:
    assert validate_category_slug("Python-AI") == "python-ai"
    assert build_category_path("sqlalchemy", "backend/python") == "backend/python/sqlalchemy"

    for invalid_slug in ["", "-python", "python-", "python_ai", "Python/AI"]:
        with pytest.raises(ValueError):
            validate_category_slug(invalid_slug)
