from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_scene(client: TestClient) -> dict[str, Any]:
    project = response_data(client.post("/api/projects", json={"title": "Draft story"}))
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
    return response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 1, "title": "Scene"},
        )
    )


def document(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def test_working_draft_updates_use_optimistic_revision_without_versions(
    client: TestClient,
) -> None:
    scene = create_scene(client)
    empty = response_data(client.get(f"/api/scenes/{scene['id']}/working-draft"))

    first = response_data(
        client.put(
            f"/api/scenes/{scene['id']}/working-draft",
            json={
                "revision": 0,
                "content_json": document("第一稿"),
                "content_markdown": "第一稿",
            },
        )
    )
    second = response_data(
        client.put(
            f"/api/scenes/{scene['id']}/working-draft",
            json={
                "revision": first["revision"],
                "content_json": document("第二稿"),
                "content_markdown": "第二稿",
            },
        )
    )
    stale = client.put(
        f"/api/scenes/{scene['id']}/working-draft",
        json={
            "revision": first["revision"],
            "content_json": document("过期覆盖"),
            "content_markdown": "过期覆盖",
        },
    )
    versions = response_data(client.get(f"/api/scenes/{scene['id']}/versions"))

    assert empty == {
        "scene_id": scene["id"],
        "content_json": {"type": "doc", "content": [{"type": "paragraph"}]},
        "content_markdown": "",
        "revision": 0,
        "updated_at": None,
    }
    assert first["revision"] == 1
    assert second["revision"] == 2
    assert second["content_markdown"] == "第二稿"
    assert stale.status_code == 409
    assert stale.json()["details"]["reason"] == "DRAFT_REVISION_CONFLICT"
    assert stale.json()["details"]["current_revision"] == 2
    assert versions == []


def test_manual_version_stores_tiptap_json_and_rejects_html_markdown(
    client: TestClient,
) -> None:
    scene = create_scene(client)
    content_json = {
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "规范",
                        "marks": [{"type": "bold"}],
                    },
                    {"type": "text", "text": "正文"},
                ],
            }
        ],
    }

    version = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={
                "content_json": content_json,
                "content_markdown": "**规范**正文",
            },
        )
    )
    invalid = client.post(
        f"/api/scenes/{scene['id']}/versions",
        json={
            "content_json": content_json,
            "content_markdown": "<p><strong>HTML</strong></p>",
        },
    )
    immutable = client.patch(
        f"/api/scene-versions/{version['id']}",
        json={"content_markdown": "不能修改"},
    )
    mismatched = client.post(
        f"/api/scenes/{scene['id']}/versions",
        json={
            "content_json": document("规范正文"),
            "content_markdown": "**规范**正文",
        },
    )

    assert version["content_json"]["content"][0]["content"] == content_json["content"][0]["content"]
    assert "nodeId" in version["content_json"]["content"][0]["attrs"]
    assert version["content_markdown"] == "**规范**正文"
    assert version["content_text"] == "规范正文"
    assert version["document_schema_version"] == "novelflow.tiptap.v2"
    assert len(version["document_hash"]) == 64
    assert invalid.status_code == 422
    assert immutable.status_code == 405
    assert mismatched.status_code == 422
    assert mismatched.json()["details"]["reason"] == "DOCUMENT_REPRESENTATION_MISMATCH"
