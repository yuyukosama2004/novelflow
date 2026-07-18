from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import memory as memory_api
from app.api import review as review_api
from app.models.memory import MemoryCandidate


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_story(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    project = response_data(client.post("/api/projects", json={"title": "Memory story"}))
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
    version = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "The bell rang."},
        )
    )
    return scene, version


class NoIssueReviewer:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, *_: Any) -> list[Any]:
        return []


class SuccessfulCurator:
    call_count = 0

    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "memory prompt"

    async def extract(self, version: Any, *_: Any) -> list[MemoryCandidate]:
        type(self).call_count += 1
        return [
            MemoryCandidate(
                scene_version_id=version.id,
                candidate_type="timeline_event",
                target_entity_type="scene",
                target_entity_id=None,
                content_json={
                    "event_text": f"Bell {type(self).call_count}",
                    "affected_character_ids": [],
                },
                evidence="The bell rang.",
                confidence=0.9,
                status="pending",
            )
        ]


class FailingCurator:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "memory prompt"

    async def extract(self, *_: Any) -> list[MemoryCandidate]:
        raise RuntimeError("provider-secret-detail")


def approve_version(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    scene_id: str,
    version_id: str,
) -> None:
    monkeypatch.setattr(review_api, "ContinuityReviewer", NoIssueReviewer)
    response_data(client.post(f"/api/scene-versions/{version_id}/review"))
    response_data(
        client.post(
            f"/api/scenes/{scene_id}/approve-version",
            json={"version_id": version_id},
        )
    )


def error_reason(response: Any) -> str:
    return response.json()["details"]["reason"]


def test_each_extraction_creates_an_independent_run(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, version = create_story(client)
    SuccessfulCurator.call_count = 0
    monkeypatch.setattr(memory_api, "MemoryCurator", SuccessfulCurator)

    first = response_data(client.post(f"/api/scene-versions/{version['id']}/extract-memories"))
    second = response_data(client.post(f"/api/scene-versions/{version['id']}/extract-memories"))
    listed_candidates = response_data(client.get(f"/api/scene-versions/{version['id']}/candidates"))

    assert first["run"]["status"] == "completed"
    assert second["run"]["status"] == "completed"
    assert first["run"]["id"] != second["run"]["id"]
    assert first["candidates"][0]["extraction_run_id"] == first["run"]["id"]
    assert second["candidates"][0]["extraction_run_id"] == second["run"]["id"]
    assert {candidate["extraction_run_id"] for candidate in listed_candidates} == {
        first["run"]["id"],
        second["run"]["id"],
    }


def test_draft_candidate_cannot_be_applied_but_can_be_rejected(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, version = create_story(client)
    monkeypatch.setattr(memory_api, "MemoryCurator", SuccessfulCurator)
    extraction = response_data(client.post(f"/api/scene-versions/{version['id']}/extract-memories"))
    candidate_id = extraction["candidates"][0]["id"]

    apply_response = client.patch(
        f"/api/candidates/{candidate_id}",
        json={"status": "approved"},
    )
    rejected = response_data(
        client.patch(
            f"/api/candidates/{candidate_id}",
            json={"status": "rejected"},
        )
    )

    assert apply_response.status_code == 409
    assert error_reason(apply_response) == "CANDIDATE_SOURCE_NOT_APPROVED"
    assert rejected["status"] == "rejected"


def test_scene_completion_requires_extraction_and_no_pending_candidates(
    client: TestClient,
    database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene, version = create_story(client)
    approve_version(client, monkeypatch, scene["id"], version["id"])

    missing_extraction = client.post(f"/api/scenes/{scene['id']}/complete")
    assert missing_extraction.status_code == 409
    assert error_reason(missing_extraction) == "MEMORY_EXTRACTION_REQUIRED"

    monkeypatch.setattr(memory_api, "MemoryCurator", SuccessfulCurator)
    extraction = response_data(client.post(f"/api/scene-versions/{version['id']}/extract-memories"))
    candidate_id = extraction["candidates"][0]["id"]

    pending = client.post(f"/api/scenes/{scene['id']}/complete")
    assert pending.status_code == 409
    assert error_reason(pending) == "PENDING_MEMORY_CANDIDATES"

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "UPDATE scenes SET approved_version_id = NULL WHERE id = ?",
            (scene["id"],),
        )
        connection.commit()

    applied = response_data(
        client.patch(
            f"/api/candidates/{candidate_id}",
            json={"status": "approved"},
        )
    )
    repeated = response_data(
        client.patch(
            f"/api/candidates/{candidate_id}",
            json={"status": "approved"},
        )
    )
    completed = response_data(client.post(f"/api/scenes/{scene['id']}/complete"))

    assert applied["status"] == "approved"
    assert repeated["id"] == applied["id"]
    assert completed["status"] == "completed"


def test_failed_extraction_run_is_visible_without_exception_leak(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, version = create_story(client)
    monkeypatch.setattr(memory_api, "MemoryCurator", FailingCurator)

    response = client.post(f"/api/scene-versions/{version['id']}/extract-memories")
    runs = response_data(client.get(f"/api/scene-versions/{version['id']}/memory-extraction-runs"))

    assert response.status_code == 500
    assert "provider-secret-detail" not in response.text
    assert runs[0]["status"] == "failed"
    assert runs[0]["completed_at"] is not None
