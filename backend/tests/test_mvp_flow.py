from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import review as review_api


class NoIssueReviewer:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, *_: Any) -> list[Any]:
        return []


def data(response):
    assert response.status_code < 400, response.text
    return response.json()["data"]


def test_project_to_scene_version_export_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = data(
        client.post(
            "/api/projects",
            json={
                "title": "雨夜档案",
                "genre": "悬疑",
                "pov_type": "third_person_limited",
                "tone": "克制",
            },
        )
    )
    character = data(
        client.post(
            f"/api/projects/{project['id']}/characters",
            json={"name": "林默", "role": "调查记者"},
        )
    )
    state = data(
        client.post(
            f"/api/characters/{character['id']}/states",
            json={
                "timeline_order": 1,
                "emotional_state": "戒备",
                "injuries_json": {"left_arm": "轻伤"},
            },
        )
    )
    assert state["injuries_json"]["left_arm"] == "轻伤"

    world = data(
        client.post(
            f"/api/projects/{project['id']}/world-entries",
            json={
                "entry_type": "location",
                "name": "市立医院",
                "canon_status": "candidate",
            },
        )
    )
    approved_world = data(client.post(f"/api/world-entries/{world['id']}/approve"))
    assert approved_world["canon_status"] == "approved"

    volume = data(
        client.post(
            f"/api/projects/{project['id']}/volumes",
            json={"sequence_no": 1, "title": "第一卷"},
        )
    )
    chapter = data(
        client.post(
            f"/api/volumes/{volume['id']}/chapters",
            json={"sequence_no": 1, "title": "医院走廊"},
        )
    )
    scene = data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={
                "sequence_no": 1,
                "title": "试探",
                "pov_character_id": character["id"],
                "story_time_order": 10,
            },
        )
    )
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={
                "content_markdown": "苏岚在走廊拦住林默。",
                "summary": "苏岚试探林默。",
                "source_type": "human",
            },
        )
    )
    assert version["version_no"] == 1

    monkeypatch.setattr(review_api, "ContinuityReviewer", NoIssueReviewer)
    data(client.post(f"/api/scene-versions/{version['id']}/review"))

    approved_scene = data(
        client.post(
            f"/api/scenes/{scene['id']}/approve-version",
            json={"version_id": version["id"]},
        )
    )
    assert approved_scene["approved_version_id"] == version["id"]

    markdown = client.get(f"/api/projects/{project['id']}/exports/markdown")
    assert markdown.status_code == 200
    assert "苏岚在走廊拦住林默" in markdown.text

    backup = data(client.get(f"/api/projects/{project['id']}/exports/json"))
    assert backup["project"]["title"] == "雨夜档案"
    assert len(backup["scene_versions"]) == 1
