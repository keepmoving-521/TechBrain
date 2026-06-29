"""Knowledge homepage API tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document


def _markdown(
    root: Path,
    document_id: str,
    *,
    category: str,
    tags: tuple[str, ...],
    status: str,
    updated_at: str,
) -> MarkdownFile:
    path = root / category / f"{document_id}.md"
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
        relative_path=f"{category}/{document_id}.md",
        size_bytes=path.stat().st_size,
    )


def _seed_overview(app) -> None:
    root = Path(".pytest_tmp") / "knowledge_overview"
    definitions = (
        ("python-published", "backend/python", ("ORM", "database"), "published", "12:00:00"),
        ("python-deprecated", "backend/python", ("database",), "deprecated", "11:00:00"),
        ("mysql-published", "database/mysql", ("performance",), "published", "12:00:00"),
        ("python-draft", "backend/python", ("ORM",), "draft", "13:00:00"),
        ("mysql-archived", "database/mysql", ("ORM",), "archived", "10:00:00"),
        ("deleted-published", "backend/python", ("ORM",), "published", "14:00:00"),
    )
    with app.state.database.session_factory() as session:
        for document_id, category, tags, status, time in definitions:
            result = sync_markdown_document(
                session,
                _markdown(
                    root,
                    document_id,
                    category=category,
                    tags=tags,
                    status=status,
                    updated_at=f"2026-06-29T{time}+08:00",
                ),
            )
            assert result.document is not None
            if document_id == "deleted-published":
                result.document.is_deleted = True
        session.commit()


def test_knowledge_overview_returns_empty_guidance_state(app) -> None:
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/knowledge/overview")

    assert response.status_code == 200
    assert response.json() == {
        "is_empty": True,
        "statistics": {
            "document_count": 0,
            "published_document_count": 0,
            "draft_document_count": 0,
            "category_count": 0,
            "tag_count": 0,
        },
        "recent_documents": [],
        "popular_categories": [],
        "popular_tags": [],
    }


def test_knowledge_overview_counts_filters_and_ranks_entries(app) -> None:
    Base.metadata.create_all(app.state.database.engine)
    _seed_overview(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/knowledge/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_empty"] is False
    assert payload["statistics"] == {
        "document_count": 5,
        "published_document_count": 3,
        "draft_document_count": 1,
        "category_count": 4,
        "tag_count": 3,
    }
    assert [item["document_id"] for item in payload["recent_documents"]] == [
        "mysql-published",
        "python-published",
        "python-deprecated",
    ]
    assert [(item["path"], item["document_count"]) for item in payload["popular_categories"]] == [
        ("backend/python", 2),
        ("database/mysql", 1),
    ]
    assert [(item["name"], item["usage_count"]) for item in payload["popular_tags"]] == [
        ("database", 2),
        ("ORM", 1),
        ("performance", 1),
    ]
