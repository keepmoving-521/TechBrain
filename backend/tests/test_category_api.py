"""Knowledge category query API tests."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import KnowledgeCategory


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
