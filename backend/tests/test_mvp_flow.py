from __future__ import annotations

from fastapi.testclient import TestClient


def data(response):
    assert response.status_code < 400, response.text
    return response.json()["data"]


def test_project_to_scene_version_export_flow(client: TestClient) -> None:
    project = data(
        client.post(
            "/api/projects",
            json={
                "title": "雨夜档案",
                "genre": "悬疑",
                "pov_type": "第三人称限知",
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
                "timeline_order": 10,
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
