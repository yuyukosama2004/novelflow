from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import review as review_api
from app.models.review import ReviewIssue


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_story(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    project = response_data(client.post("/api/projects", json={"title": "Approval story"}))
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
    return chapter, scene


def create_version(
    client: TestClient,
    scene_id: str,
    content: str = "Reviewed content.",
) -> dict[str, Any]:
    return response_data(
        client.post(
            f"/api/scenes/{scene_id}/versions",
            json={"content_markdown": content},
        )
    )


class BaseReviewer:
    severity: str | None = None

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, version: Any, *_: Any) -> list[ReviewIssue]:
        if self.severity is None:
            return []
        return [
            ReviewIssue(
                scene_version_id=version.id,
                issue_type="continuity",
                severity=self.severity,
                evidence_json="{}",
                conflict_rule="rule",
                suggestion="suggestion",
                confidence=0.9,
                status="open",
            )
        ]


class NoIssueReviewer(BaseReviewer):
    pass


class BlockingReviewer(BaseReviewer):
    severity = "blocking"


class MediumReviewer(BaseReviewer):
    severity = "medium"


def review_version(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    version_id: str,
    reviewer: type[BaseReviewer],
) -> dict[str, Any]:
    monkeypatch.setattr(review_api, "ContinuityReviewer", reviewer)
    return response_data(client.post(f"/api/scene-versions/{version_id}/review"))


def approval_reason(response: Any) -> str:
    return response.json()["details"]["reason"]


def test_unreviewed_and_empty_versions_cannot_be_approved(client: TestClient) -> None:
    _, scene = create_story(client)
    unreviewed = create_version(client, scene["id"])
    empty = create_version(client, scene["id"], "   ")

    unreviewed_response = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": unreviewed["id"]},
    )
    empty_response = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": empty["id"]},
    )

    assert unreviewed_response.status_code == 409
    assert approval_reason(unreviewed_response) == "VERSION_REVIEW_REQUIRED"
    assert empty_response.status_code == 422
    assert approval_reason(empty_response) == "EMPTY_VERSION_CONTENT"


def test_completed_review_without_blocking_issue_can_be_approved(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, scene = create_story(client)
    version = create_version(client, scene["id"])
    review_version(client, monkeypatch, version["id"], NoIssueReviewer)

    approved = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/approve-version",
            json={"version_id": version["id"]},
        )
    )
    refreshed_version = response_data(client.get(f"/api/scene-versions/{version['id']}"))

    assert approved["approved_version_id"] == version["id"]
    assert approved["status"] == "canonicalizing"
    assert refreshed_version["approved_at"] is not None
    assert refreshed_version["approval_override_reason"] is None


def test_blocking_issue_requires_non_empty_override_reason(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, scene = create_story(client)
    version = create_version(client, scene["id"])
    review = review_version(client, monkeypatch, version["id"], BlockingReviewer)

    blocked = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": version["id"]},
    )
    response_data(
        client.patch(
            f"/api/issues/{review['issues'][0]['id']}",
            json={"status": "ignored"},
        )
    )
    ignored_blocked = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": version["id"]},
    )
    blank_override = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": version["id"], "override_reason": "   "},
    )

    assert blocked.status_code == 409
    assert approval_reason(blocked) == "BLOCKING_REVIEW_ISSUES"
    assert ignored_blocked.status_code == 409
    assert blank_override.status_code == 409

    approved = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/approve-version",
            json={
                "version_id": version["id"],
                "override_reason": "作者确认该冲突是有意安排",
            },
        )
    )
    refreshed_version = response_data(client.get(f"/api/scene-versions/{version['id']}"))
    assert approved["approved_version_id"] == version["id"]
    assert refreshed_version["approval_override_reason"] == "作者确认该冲突是有意安排"


def test_non_blocking_issue_does_not_require_override(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, scene = create_story(client)
    version = create_version(client, scene["id"])
    review_version(client, monkeypatch, version["id"], MediumReviewer)

    approved = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": version["id"]},
    )

    assert approved.status_code == 200


def test_replacing_an_existing_approved_version_is_not_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, scene = create_story(client)
    first = create_version(client, scene["id"], "First.")
    review_version(client, monkeypatch, first["id"], NoIssueReviewer)
    response_data(
        client.post(
            f"/api/scenes/{scene['id']}/approve-version",
            json={"version_id": first["id"]},
        )
    )

    second = create_version(client, scene["id"], "Second.")
    review_version(client, monkeypatch, second["id"], NoIssueReviewer)
    replacement = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": second["id"]},
    )

    assert replacement.status_code == 409
    assert approval_reason(replacement) == "HISTORICAL_REPLACEMENT_NOT_READY"
