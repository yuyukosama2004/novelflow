from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "ok"
    assert response.headers["x-request-id"].startswith("req_")


def test_cors_allows_loopback_dev_origin(client: TestClient) -> None:
    response = client.get(
        "/api/health",
        headers={"Origin": "http://127.0.0.1:5173"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
