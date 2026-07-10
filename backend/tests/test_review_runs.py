from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import review as review_api
from app.models.review import ReviewIssue


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_scene_version(client: TestClient) -> dict[str, Any]:
    project = response_data(client.post("/api/projects", json={"title": "Review story"}))
    volume = response_data(
        client.post(
            f"/api/projects/{project['id']}/volumes",
            json={"sequence_no": 1, "title": "Volume"},
        )
    )
    chapter = response_data(
        client.post(
            f"/api/volumes/{volume['id']}/chapters",
            json={"sequence_no": 1, "title": "Chapter"},
        )
    )
    scene = response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 1, "title": "Scene"},
        )
    )
    return response_data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "A test scene."},
        )
    )


class SuccessfulReviewer:
    call_count = 0

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, version: Any, *_: Any) -> list[ReviewIssue]:
        type(self).call_count += 1
        return [
            ReviewIssue(
                scene_version_id=version.id,
                issue_type=f"round_{type(self).call_count}",
                severity="high",
                evidence_json="{}",
                conflict_rule="rule",
                suggestion="suggestion",
                confidence=0.9,
                status="open",
            )
        ]


class FailingReviewer:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, *_: Any) -> list[ReviewIssue]:
        raise RuntimeError("provider-secret-detail")


def test_each_review_creates_an_independent_run(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version = create_scene_version(client)
    SuccessfulReviewer.call_count = 0
    monkeypatch.setattr(review_api, "ContinuityReviewer", SuccessfulReviewer)

    first = response_data(client.post(f"/api/scene-versions/{version['id']}/review"))
    second = response_data(client.post(f"/api/scene-versions/{version['id']}/review"))

    assert first["run"]["status"] == "completed"
    assert second["run"]["status"] == "completed"
    assert first["run"]["id"] != second["run"]["id"]
    assert first["issues"][0]["issue_type"] == "round_1"
    assert second["issues"][0]["issue_type"] == "round_2"
    assert first["issues"][0]["review_run_id"] == first["run"]["id"]
    assert second["issues"][0]["review_run_id"] == second["run"]["id"]

    runs = response_data(client.get(f"/api/scene-versions/{version['id']}/review-runs"))
    assert [run["id"] for run in runs] == [second["run"]["id"], first["run"]["id"]]

    first_round = response_data(client.get(f"/api/review-runs/{first['run']['id']}"))
    second_round = response_data(client.get(f"/api/review-runs/{second['run']['id']}"))
    assert [issue["issue_type"] for issue in first_round["issues"]] == ["round_1"]
    assert [issue["issue_type"] for issue in second_round["issues"]] == ["round_2"]


def test_failed_review_run_is_persisted_without_leaking_exception(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    version = create_scene_version(client)
    monkeypatch.setattr(review_api, "ContinuityReviewer", FailingReviewer)

    response = client.post(f"/api/scene-versions/{version['id']}/review")

    assert response.status_code == 500
    assert "provider-secret-detail" not in response.text

    runs = response_data(client.get(f"/api/scene-versions/{version['id']}/review-runs"))
    assert len(runs) == 1
    assert runs[0]["status"] == "failed"
    assert runs[0]["completed_at"] is not None
    assert "provider-secret-detail" not in runs[0]["summary"]
