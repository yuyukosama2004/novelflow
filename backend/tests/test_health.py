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
