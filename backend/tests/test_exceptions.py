"""Exception response tests."""

from fastapi import FastAPI, HTTPException, Query
from fastapi.testclient import TestClient


def test_not_found_uses_unified_error_response(client: TestClient) -> None:
    response = client.get(
        "/api/v1/missing",
        headers={"X-Request-ID": "not-found-test"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "HTTP_404",
            "message": "Not Found",
            "details": None,
        },
        "request_id": "not-found-test",
    }


def test_validation_error_uses_unified_error_response(
    app: FastAPI,
    client: TestClient,
) -> None:
    @app.get("/test-validation")
    async def validation_route(limit: int = Query(ge=1)) -> dict[str, int]:
        return {"limit": limit}

    response = client.get("/test-validation?limit=0")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "请求参数校验失败"
    assert body["error"]["details"][0]["field"] == "query.limit"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_http_exception_preserves_safe_details(
    app: FastAPI,
    client: TestClient,
) -> None:
    @app.get("/test-http-error")
    async def http_error_route() -> None:
        raise HTTPException(status_code=409, detail="资源状态冲突")

    response = client.get("/test-http-error")

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "HTTP_409",
        "message": "资源状态冲突",
        "details": None,
    }


def test_unhandled_exception_hides_internal_details(
    app: FastAPI,
    client: TestClient,
) -> None:
    @app.get("/test-unhandled-error")
    async def unhandled_error_route() -> None:
        raise RuntimeError("sensitive implementation detail")

    response = client.get(
        "/test-unhandled-error",
        headers={"X-Request-ID": "unhandled-test"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "details": None,
        },
        "request_id": "unhandled-test",
    }
    assert "sensitive implementation detail" not in response.text
