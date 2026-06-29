"""Knowledge document detail API tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from techbrain.db.base import Base
from techbrain.knowledge.scanner import MarkdownFile
from techbrain.knowledge.sync import sync_markdown_document


def _markdown(root: Path, document_id: str) -> MarkdownFile:
    path = root / "backend" / "python" / f"{document_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
schema_version: 1
id: {document_id}
title: SQLAlchemy 加载策略
category: backend/python
tags:
  - ORM
  - SQLAlchemy
status: published
created_at: 2026-06-20T10:00:00+08:00
updated_at: 2026-06-29T12:00:00+08:00
summary: 理解 joinedload 与 contains_eager。
source:
  type: summary
  url: https://docs.sqlalchemy.org/
aliases:
  - joinedload
language: zh-CN
visibility: private
---

# SQLAlchemy 加载策略

正文包含 `joinedload` 示例。
""",
        encoding="utf-8",
    )
    return MarkdownFile(
        path=path.resolve(),
        relative_path=f"backend/python/{document_id}.md",
        size_bytes=path.stat().st_size,
    )


def _seed_documents(app) -> tuple[int, int]:
    root = Path(".pytest_tmp") / "document_detail"
    Base.metadata.create_all(app.state.database.engine)
    with app.state.database.session_factory() as session:
        active = sync_markdown_document(session, _markdown(root, "sqlalchemy-loading"))
        deleted = sync_markdown_document(session, _markdown(root, "deleted-document"))
        assert active.document is not None
        assert deleted.document is not None
        deleted.document.is_deleted = True
        deleted.document.sync_status = "deleted"
        session.commit()
        return active.document.id, deleted.document.id


def test_document_detail_returns_complete_content_metadata_and_sync_state(app) -> None:
    active_id, _ = _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(f"/api/v1/documents/{active_id}")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "id",
        "document_id",
        "title",
        "summary",
        "body",
        "category_id",
        "category",
        "tags",
        "aliases",
        "status",
        "visibility",
        "language",
        "source",
        "relative_path",
        "created_at",
        "updated_at",
        "sync",
        "record_created_at",
        "record_updated_at",
    }
    assert payload["id"] == active_id
    assert payload["document_id"] == "sqlalchemy-loading"
    assert payload["title"] == "SQLAlchemy 加载策略"
    assert "正文包含 `joinedload` 示例。" in payload["body"]
    assert payload["category"] == "backend/python"
    assert payload["tags"] == ["ORM", "SQLAlchemy"]
    assert payload["aliases"] == ["joinedload"]
    assert payload["source"] == {
        "type": "summary",
        "url": "https://docs.sqlalchemy.org/",
    }
    assert payload["relative_path"] == "backend/python/sqlalchemy-loading.md"
    assert "absolute_path" not in payload
    assert payload["sync"]["status"] == "synced"
    assert payload["sync"]["error"] is None
    assert payload["sync"]["last_scanned_at"] is not None
    assert payload["sync"]["last_synced_at"] is not None
    assert len(payload["sync"]["path_hash"]) == 64
    assert len(payload["sync"]["content_hash"]) == 64
    assert len(payload["sync"]["front_matter_hash"]) == 64


def test_document_detail_distinguishes_missing_and_soft_deleted_documents(app) -> None:
    _, deleted_id = _seed_documents(app)

    with TestClient(app, raise_server_exceptions=False) as client:
        deleted = client.get(f"/api/v1/documents/{deleted_id}")
        missing = client.get("/api/v1/documents/999999")
        invalid = client.get("/api/v1/documents/0")

    assert deleted.status_code == 410
    assert deleted.json()["error"] == {
        "code": "HTTP_410",
        "message": "文档已删除",
        "details": None,
    }
    assert missing.status_code == 404
    assert missing.json()["error"] == {
        "code": "HTTP_404",
        "message": "文档不存在",
        "details": None,
    }
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
