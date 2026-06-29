"""Knowledge document list API tests."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import KnowledgeCategory, KnowledgeTag


def _write_markdown(
    root: Path,
    file_name: str,
    document_id: str,
    *,
    category: str,
    tags: tuple[str, ...],
    status: str,
    updated_at: str,
) -> MarkdownFile:
    path = root / category / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    tags_yaml = "tags: []" if not tags else "tags:\n" + "\n".join(f"  - {tag}" for tag in tags)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {document_id} title
category: {category}
{tags_yaml}
status: {status}
created_at: 2026-06-29T09:00:00+08:00
updated_at: {updated_at}
summary: {document_id} summary
---

# {document_id}
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path=f"{category}/{file_name}",
        size_bytes=path.stat().st_size,
    )


def _seed_documents(app) -> dict[str, dict[str, int]]:
    root = Path(".pytest_tmp") / "document_api"
    Base.metadata.create_all(app.state.database.engine)
    definitions = (
        (
            "published-python",
            "published-python.md",
            "backend/python",
            ("orm",),
            "published",
            "2026-06-29T12:00:00+08:00",
        ),
        (
            "deprecated-python",
            "deprecated-python.md",
            "backend/python",
            ("database",),
            "deprecated",
            "2026-06-29T11:00:00+08:00",
        ),
        (
            "draft-python",
            "draft-python.md",
            "backend/python",
            ("orm",),
            "draft",
            "2026-06-29T13:00:00+08:00",
        ),
        (
            "archived-mysql",
            "archived-mysql.md",
            "database/mysql",
            ("orm",),
            "archived",
            "2026-06-29T10:00:00+08:00",
        ),
        (
            "deleted-published",
            "deleted-published.md",
            "backend/python",
            ("orm",),
            "published",
            "2026-06-29T14:00:00+08:00",
        ),
        (
            "published-mysql",
            "published-mysql.md",
            "database/mysql",
            ("performance",),
            "published",
            "2026-06-29T12:00:00+08:00",
        ),
    )

    document_ids: dict[str, int] = {}
    with app.state.database.session_factory() as session:
        for document_id, file_name, category, tags, status, updated_at in definitions:
            result = sync_markdown_document(
                session,
                _write_markdown(
                    root,
                    file_name,
                    document_id,
                    category=category,
                    tags=tags,
                    status=status,
                    updated_at=updated_at,
                ),
            )
            assert result.document is not None
            document_ids[document_id] = result.document.id
            if document_id == "deleted-published":
                result.document.is_deleted = True
        session.commit()

        categories = {
            category.path: category.id for category in session.scalars(select(KnowledgeCategory))
        }
        tags = {tag.normalized_name: tag.id for tag in session.scalars(select(KnowledgeTag))}
    return {"documents": document_ids, "categories": categories, "tags": tags}


def test_document_list_default_visibility_pagination_and_stable_sort(app) -> None:
    ids = _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        first_page = client.get("/api/v1/documents?page=1&page_size=2")
        second_page = client.get("/api/v1/documents?page=2&page_size=2")

    assert first_page.status_code == 200
    assert [item["document_id"] for item in first_page.json()["items"]] == [
        "published-mysql",
        "published-python",
    ]
    assert [item["id"] for item in first_page.json()["items"]] == [
        ids["documents"]["published-mysql"],
        ids["documents"]["published-python"],
    ]
    assert first_page.json()["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total": 3,
        "total_pages": 2,
        "has_previous": False,
        "has_next": True,
    }
    assert [item["document_id"] for item in second_page.json()["items"]] == ["deprecated-python"]
    assert second_page.json()["pagination"]["has_previous"] is True


def test_document_list_supports_ascending_updated_at_sort(app) -> None:
    _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/documents?sort=updated_at")

    assert response.status_code == 200
    assert [item["document_id"] for item in response.json()["items"]] == [
        "deprecated-python",
        "published-python",
        "published-mysql",
    ]


def test_document_list_explicit_status_filter_can_include_drafts_and_archived(app) -> None:
    _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/documents?status=draft,archived")

    assert response.status_code == 200
    assert [item["document_id"] for item in response.json()["items"]] == [
        "draft-python",
        "archived-mysql",
    ]
    assert response.json()["pagination"]["total"] == 2


def test_document_list_filters_by_direct_category_and_structured_tag(app) -> None:
    ids = _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        category_response = client.get(
            "/api/v1/documents",
            params={"category_id": ids["categories"]["backend/python"]},
        )
        tag_response = client.get(
            "/api/v1/documents",
            params={"tag_id": ids["tags"]["orm"]},
        )
        all_orm_statuses = client.get(
            "/api/v1/documents",
            params={
                "tag_id": ids["tags"]["orm"],
                "status": "published,draft,archived",
            },
        )

    assert [item["document_id"] for item in category_response.json()["items"]] == [
        "published-python",
        "deprecated-python",
    ]
    assert [item["document_id"] for item in tag_response.json()["items"]] == ["published-python"]
    assert [item["document_id"] for item in all_orm_statuses.json()["items"]] == [
        "draft-python",
        "published-python",
        "archived-mysql",
    ]


def test_document_list_filters_by_source_updated_at_range(app) -> None:
    _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/documents",
            params={
                "updated_from": "2026-06-29T11:30:00+08:00",
                "updated_to": "2026-06-29T12:00:00+08:00",
                "sort": "updated_at",
            },
        )

    assert response.status_code == 200
    assert [item["document_id"] for item in response.json()["items"]] == [
        "published-python",
        "published-mysql",
    ]


def test_document_list_returns_empty_page_and_validates_filters(app) -> None:
    _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        empty = client.get("/api/v1/documents?category_id=9999")
        invalid_status = client.get("/api/v1/documents?status=unknown")
        invalid_range = client.get(
            "/api/v1/documents",
            params={
                "updated_from": "2026-06-30T00:00:00+08:00",
                "updated_to": "2026-06-29T00:00:00+08:00",
            },
        )
        invalid_sort = client.get("/api/v1/documents?sort=title")

    assert empty.status_code == 200
    assert empty.json()["items"] == []
    assert empty.json()["pagination"]["total"] == 0
    assert invalid_status.status_code == 400
    assert "不支持的文档状态" in invalid_status.json()["error"]["message"]
    assert invalid_range.status_code == 400
    assert invalid_range.json()["error"]["message"] == "updated_from 不能晚于 updated_to"
    assert invalid_sort.status_code == 422
