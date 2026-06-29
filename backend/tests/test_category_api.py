"""Knowledge category query API tests."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from techbrain.core.config import Environment, Settings
from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import KnowledgeCategory, KnowledgeDocument


def _write_markdown(
    root: Path,
    relative_path: str,
    document_id: str,
    category: str,
) -> MarkdownFile:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {document_id}
category: {category}
created_at: 2026-06-29T10:00:00+08:00
updated_at: 2026-06-29T10:00:00+08:00
---

# {document_id}
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path=relative_path,
        size_bytes=path.stat().st_size,
    )


def _seed_categories(app) -> dict[str, int]:
    root = Path(".pytest_tmp") / "category_api"
    Base.metadata.create_all(app.state.database.engine)

    with app.state.database.session_factory() as session:
        sync_markdown_document(
            session,
            _write_markdown(root, "backend/root-note.md", "backend-note", "backend"),
        )
        sync_markdown_document(
            session,
            _write_markdown(root, "backend/python/python.md", "python-note", "backend/python"),
        )
        deleted = sync_markdown_document(
            session,
            _write_markdown(
                root,
                "backend/python/deleted.md",
                "deleted-python-note",
                "backend/python",
            ),
        )
        assert deleted.document is not None
        deleted.document.is_deleted = True

        backend = session.scalar(
            select(KnowledgeCategory).where(KnowledgeCategory.path == "backend")
        )
        python = session.scalar(
            select(KnowledgeCategory).where(KnowledgeCategory.path == "backend/python")
        )
        assert backend is not None
        assert python is not None
        backend.sort_order = 20
        python.sort_order = 20

        database = KnowledgeCategory(
            name="database",
            slug="database",
            path="database",
            sort_order=10,
            status="active",
        )
        go = KnowledgeCategory(
            parent=backend,
            name="go",
            slug="go",
            path="backend/go",
            sort_order=10,
            status="active",
        )
        session.add_all((database, go))
        session.commit()

        return {
            "backend": backend.id,
            "python": python.id,
            "database": database.id,
            "go": go.id,
        }


def test_get_category_tree_returns_sorted_hierarchy_and_counts(app) -> None:
    ids = _seed_categories(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/categories/tree")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["items"]] == [ids["database"], ids["backend"]]

    database, backend = payload["items"]
    assert database["document_count"] == 0
    assert database["direct_document_count"] == 0
    assert database["children"] == []
    assert backend["direct_document_count"] == 1
    assert backend["document_count"] == 2
    assert [item["id"] for item in backend["children"]] == [ids["go"], ids["python"]]
    assert backend["children"][0]["document_count"] == 0
    assert backend["children"][1]["direct_document_count"] == 1


def test_get_category_detail_returns_navigation_and_recursive_counts(app) -> None:
    ids = _seed_categories(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/categories/{ids['python']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["path"] == "backend/python"
    assert payload["direct_document_count"] == 1
    assert payload["document_count"] == 1
    assert payload["parent"]["id"] == ids["backend"]
    assert payload["parent"]["document_count"] == 2
    assert payload["children"] == []


def test_get_empty_category_detail_returns_zero_counts(app) -> None:
    ids = _seed_categories(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/categories/{ids['database']}")

    assert response.status_code == 200
    assert response.json()["document_count"] == 0
    assert response.json()["children"] == []


def test_get_category_detail_returns_404(client: TestClient) -> None:
    Base.metadata.create_all(client.app.state.database.engine)

    response = client.get("/api/v1/categories/404")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "分类不存在"


def test_create_rename_and_reorder_empty_category(app) -> None:
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        created = client.post(
            "/api/v1/categories",
            json={"name": "Backend", "slug": "backend", "sort_order": 20},
        )
        updated = client.patch(
            f"/api/v1/categories/{created.json()['id']}",
            json={"name": "后端开发", "sort_order": 5},
        )

    assert created.status_code == 201
    assert created.json()["path"] == "backend"
    assert created.json()["document_count"] == 0
    assert updated.status_code == 200
    assert updated.json()["name"] == "后端开发"
    assert updated.json()["sort_order"] == 5
    assert updated.json()["path"] == "backend"


def test_create_category_rejects_path_conflict(app) -> None:
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post(
            "/api/v1/categories",
            json={"name": "Backend", "slug": "backend"},
        )
        duplicate = client.post(
            "/api/v1/categories",
            json={"name": "Backend duplicate", "slug": "backend"},
        )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["message"] == "分类路径已存在: backend"


def test_category_management_rejects_write_while_sync_lock_is_held(app) -> None:
    Base.metadata.create_all(app.state.database.engine)
    app.state.knowledge_sync_lock.acquire()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/categories",
                json={"name": "Backend", "slug": "backend"},
            )
    finally:
        app.state.knowledge_sync_lock.release()

    assert response.status_code == 409
    assert "正在执行" in response.json()["error"]["message"]


def test_move_and_rename_category_rewrites_subtree_markdown(app) -> None:
    root = Path(".pytest_tmp") / "category_management_move"
    app.state.settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )
    Base.metadata.create_all(app.state.database.engine)

    python_file = _write_markdown(
        root,
        "backend/python/python.md",
        "python-management-note",
        "backend/python",
    )
    sqlalchemy_file = _write_markdown(
        root,
        "backend/python/sqlalchemy/sqlalchemy.md",
        "sqlalchemy-management-note",
        "backend/python/sqlalchemy",
    )
    with app.state.database.session_factory() as session:
        sync_markdown_document(session, python_file)
        sync_markdown_document(session, sqlalchemy_file)
        database = KnowledgeCategory(
            name="Database",
            slug="database",
            path="database",
            sort_order=0,
            status="active",
        )
        session.add(database)
        session.commit()
        python = session.scalar(
            select(KnowledgeCategory).where(KnowledgeCategory.path == "backend/python")
        )
        assert python is not None
        python_id = python.id
        database_id = database.id

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.patch(
            f"/api/v1/categories/{python_id}",
            json={"name": "Python Engineering", "slug": "py", "parent_id": database_id},
        )
        with app.state.database.session_factory() as session:
            paths = session.scalars(
                select(KnowledgeCategory.path).order_by(KnowledgeCategory.path)
            ).all()
            document_categories = session.scalars(
                select(KnowledgeDocument.category).order_by(KnowledgeDocument.document_id)
            ).all()

    assert response.status_code == 200
    assert response.json()["path"] == "database/py"
    assert "category: database/py\n" in python_file.path.read_text(encoding="utf-8")
    assert "category: database/py/sqlalchemy\n" in sqlalchemy_file.path.read_text(encoding="utf-8")
    assert "updated_at: 2026-06-29T10:00:00+08:00" not in python_file.path.read_text(
        encoding="utf-8"
    )

    assert "database/py" in paths
    assert "database/py/sqlalchemy" in paths
    assert document_categories == ["database/py", "database/py/sqlalchemy"]


def test_category_path_change_rejects_external_markdown_modification(app) -> None:
    root = Path(".pytest_tmp") / "category_management_conflict"
    app.state.settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )
    Base.metadata.create_all(app.state.database.engine)
    markdown_file = _write_markdown(
        root,
        "backend/python/conflict.md",
        "category-conflict-note",
        "backend/python",
    )
    with app.state.database.session_factory() as session:
        result = sync_markdown_document(session, markdown_file)
        session.commit()
        assert result.document is not None
        category_id = result.document.category_id

    external_content = markdown_file.path.read_text(encoding="utf-8").replace(
        "# category-conflict-note",
        "# externally changed",
    )
    markdown_file.path.write_text(external_content, encoding="utf-8")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.patch(
            f"/api/v1/categories/{category_id}",
            json={"slug": "python3"},
        )
        with app.state.database.session_factory() as session:
            category = session.get(KnowledgeCategory, category_id)
            assert category is not None
            category_path = category.path

    assert response.status_code == 409
    assert "已被外部修改" in response.json()["error"]["message"]
    assert "category: backend/python" in markdown_file.path.read_text(encoding="utf-8")
    assert "# externally changed" in markdown_file.path.read_text(encoding="utf-8")
    assert category_path == "backend/python"


def test_move_category_rejects_cycle_and_target_path_conflict(app) -> None:
    Base.metadata.create_all(app.state.database.engine)
    with app.state.database.session_factory() as session:
        backend = KnowledgeCategory(
            name="backend", slug="backend", path="backend", sort_order=0, status="active"
        )
        python = KnowledgeCategory(
            parent=backend,
            name="python",
            slug="python",
            path="backend/python",
            sort_order=0,
            status="active",
        )
        database = KnowledgeCategory(
            name="database", slug="database", path="database", sort_order=0, status="active"
        )
        database_python = KnowledgeCategory(
            parent=database,
            name="python",
            slug="python",
            path="database/python",
            sort_order=0,
            status="active",
        )
        session.add_all((backend, python, database, database_python))
        session.commit()
        ids = {"backend": backend.id, "python": python.id, "database": database.id}

    with TestClient(app, raise_server_exceptions=False) as client:
        cycle = client.patch(
            f"/api/v1/categories/{ids['backend']}",
            json={"parent_id": ids["python"]},
        )
        conflict = client.patch(
            f"/api/v1/categories/{ids['python']}",
            json={"parent_id": ids["database"]},
        )

    assert cycle.status_code == 409
    assert "后代分类" in cycle.json()["error"]["message"]
    assert conflict.status_code == 409
    assert conflict.json()["error"]["message"] == "目标分类路径已存在: database/python"
