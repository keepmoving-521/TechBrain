"""Health endpoint tests."""

from fastapi.testclient import TestClient


def test_live_health_check(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "TechBrain API",
        "version": "0.1.0",
        "environment": "test",
    }
    assert response.headers["X-Request-ID"]


def test_ready_health_check(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health/ready",
        headers={"X-Request-ID": "integration-test-request"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "integration-test-request"
    assert response.json()["status"] == "ok"
    assert response.json()["checks"] == [
        {"name": "configuration", "status": "ok", "message": None},
        {"name": "database", "status": "ok", "message": None},
    ]


def test_ready_health_check_returns_503_when_database_is_unavailable(app) -> None:
    class UnavailableDatabase:
        def check_connection(self):
            from techbrain.db.session import DatabaseCheckResult

            return DatabaseCheckResult(ok=False, message="database unavailable")

    app.state.database = UnavailableDatabase()

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["checks"][-1] == {
        "name": "database",
        "status": "error",
        "message": "database unavailable",
    }


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get(
        "/api/v1/health/live",
        headers={"X-Request-ID": "not valid because it contains spaces"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "not valid because it contains spaces"
    assert len(response.headers["X-Request-ID"]) == 32
