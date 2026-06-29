"""Knowledge tag query API tests."""

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document
from techbrain.models import KnowledgeTag, KnowledgeTagStatus


def _write_markdown(
    root: Path,
    file_name: str,
    document_id: str,
    *,
    tags: tuple[str, ...],
    updated_at: str,
) -> MarkdownFile:
    path = root / "backend/python" / file_name
    path.parent.mkdir(parents=True, exist_ok=True)
    tags_yaml = "\n".join(f"  - {tag}" for tag in tags)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: {document_id} title
category: backend/python
tags:
{tags_yaml}
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
        relative_path=f"backend/python/{file_name}",
        size_bytes=path.stat().st_size,
    )


def _seed_tags(app) -> dict[str, int]:
    root = Path(".pytest_tmp") / "tag_api"
    Base.metadata.create_all(app.state.database.engine)
    old_file = _write_markdown(
        root,
        "orm-old.md",
        "orm-old",
        tags=("ORM", "performance"),
        updated_at="2026-06-29T10:00:00+08:00",
    )
    new_file = _write_markdown(
        root,
        "orm-new.md",
        "orm-new",
        tags=("orm", "database"),
        updated_at="2026-06-29T12:00:00+08:00",
    )
    deleted_file = _write_markdown(
        root,
        "orm-deleted.md",
        "orm-deleted",
        tags=("orm",),
        updated_at="2026-06-29T13:00:00+08:00",
    )

    with app.state.database.session_factory() as session:
        sync_markdown_document(session, old_file)
        sync_markdown_document(session, new_file)
        deleted = sync_markdown_document(session, deleted_file)
        assert deleted.document is not None
        deleted.document.is_deleted = True
        empty = KnowledgeTag(name="empty", status=KnowledgeTagStatus.ARCHIVED.value)
        session.add(empty)
        session.commit()

        tags = session.scalars(select(KnowledgeTag)).all()
        return {tag.normalized_name: tag.id for tag in tags}


def test_list_tags_sorts_by_name_and_returns_standard_pagination(app) -> None:
    _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/tags?page=1&page_size=2&sort=name")

    assert response.status_code == 200
    payload = response.json()
    assert [item["normalized_name"] for item in payload["items"]] == ["database", "empty"]
    assert [item["usage_count"] for item in payload["items"]] == [1, 0]
    assert payload["pagination"] == {
        "page": 1,
        "page_size": 2,
        "total": 4,
        "total_pages": 2,
        "has_previous": False,
        "has_next": True,
    }


def test_list_tags_sorts_by_usage_count_and_supports_descending_name(app) -> None:
    _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        usage_response = client.get("/api/v1/tags?sort=-usage_count")
        name_response = client.get("/api/v1/tags?sort=-name")

    assert usage_response.status_code == 200
    assert [item["normalized_name"] for item in usage_response.json()["items"]] == [
        "orm",
        "database",
        "performance",
        "empty",
    ]
    assert [item["usage_count"] for item in usage_response.json()["items"]] == [2, 1, 1, 0]
    assert [item["normalized_name"] for item in name_response.json()["items"]] == [
        "performance",
        "orm",
        "empty",
        "database",
    ]


def test_get_tag_detail_returns_usage_count_excluding_deleted_documents(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/tags/{ids['orm']}")

    assert response.status_code == 200
    assert response.json()["normalized_name"] == "orm"
    assert response.json()["usage_count"] == 2
    assert response.json()["status"] == "active"


def test_list_tag_documents_is_paginated_and_excludes_deleted_documents(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        first_page = client.get(f"/api/v1/tags/{ids['orm']}/documents?page=1&page_size=1")
        second_page = client.get(f"/api/v1/tags/{ids['orm']}/documents?page=2&page_size=1")

    assert first_page.status_code == 200
    assert [item["document_id"] for item in first_page.json()["items"]] == ["orm-new"]
    assert first_page.json()["pagination"]["total"] == 2
    assert first_page.json()["pagination"]["total_pages"] == 2
    assert first_page.json()["pagination"]["has_next"] is True
    assert [item["document_id"] for item in second_page.json()["items"]] == ["orm-old"]
    assert second_page.json()["pagination"]["has_previous"] is True


def test_empty_tag_returns_zero_usage_and_empty_document_page(app) -> None:
    ids = _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        detail = client.get(f"/api/v1/tags/{ids['empty']}")
        documents = client.get(f"/api/v1/tags/{ids['empty']}/documents")

    assert detail.status_code == 200
    assert detail.json()["usage_count"] == 0
    assert documents.status_code == 200
    assert documents.json()["items"] == []
    assert documents.json()["pagination"]["total"] == 0
    assert documents.json()["pagination"]["total_pages"] == 0


def test_tag_queries_return_404_and_validate_sort(app) -> None:
    _seed_tags(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        detail = client.get("/api/v1/tags/9999")
        documents = client.get("/api/v1/tags/9999/documents")
        invalid_sort = client.get("/api/v1/tags?sort=created_at")

    assert detail.status_code == 404
    assert detail.json()["error"]["message"] == "标签不存在"
    assert documents.status_code == 404
    assert invalid_sort.status_code == 422
    assert invalid_sort.json()["error"]["code"] == "VALIDATION_ERROR"
