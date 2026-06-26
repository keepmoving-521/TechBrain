"""Knowledge synchronization API tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from techbrain.core.config import Environment, Settings
from techbrain.db.base import Base


def _write_markdown(root: Path) -> None:
    path = root / "backend/python/sqlalchemy-joinedload.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
---

# SQLAlchemy joinedload 使用指南
""",
        encoding="utf-8",
    )


def test_trigger_knowledge_sync_creates_task(app) -> None:
    root = Path(".pytest_tmp") / "api_sync_create"
    _write_markdown(root)
    app.state.settings = Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve(),
    )
    Base.metadata.create_all(app.state.database.engine)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/knowledge/sync")
        list_response = client.get("/api/v1/knowledge/sync/tasks")
        task_response = client.get(f"/api/v1/knowledge/sync/tasks/{response.json()['id']}")

    assert response.status_code == 201
    assert response.json()["status"] == "success"
    assert response.json()["scanned_count"] == 1
    assert response.json()["created_count"] == 1
    assert response.json()["failures"] == []
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert task_response.status_code == 200
    assert task_response.json()["id"] == response.json()["id"]


def test_trigger_knowledge_sync_returns_configuration_error(client: TestClient) -> None:
    response = client.post("/api/v1/knowledge/sync")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "HTTP_400"
    assert "TECHBRAIN_KNOWLEDGE_ROOT" in response.json()["error"]["message"]


def test_trigger_knowledge_sync_rejects_concurrent_request(app) -> None:
    app.state.knowledge_sync_lock.acquire()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/knowledge/sync")
    finally:
        app.state.knowledge_sync_lock.release()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "HTTP_409"


def test_get_knowledge_sync_task_returns_404(client: TestClient) -> None:
    Base.metadata.create_all(client.app.state.database.engine)

    response = client.get("/api/v1/knowledge/sync/tasks/404")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "同步任务不存在"
