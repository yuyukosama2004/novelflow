from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.documents.codec import (
    CANONICAL_DOCUMENT_SCHEMA,
    SceneDocumentError,
    build_scene_document,
    ensure_scene_node_ids,
)


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_scene(client: TestClient) -> dict[str, Any]:
    project = response_data(client.post("/api/projects", json={"title": "Document story"}))
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


def test_markdown_only_input_builds_canonical_rich_document(client: TestClient) -> None:
    scene = create_scene(client)
    markdown = "# 标题\n\n**重点**  \n下一行\n\n- 甲\n- 乙"

    version = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": markdown},
        )
    )

    assert version["content_markdown"] == markdown
    assert version["content_text"] == "标题\n重点\n下一行\n甲\n乙"
    heading = version["content_json"]["content"][0]
    assert heading["type"] == "heading"
    assert heading["attrs"]["level"] == 1
    assert str(UUID(heading["attrs"]["nodeId"])) == heading["attrs"]["nodeId"]
    assert heading["content"] == [{"type": "text", "text": "标题"}]
    assert version["document_schema_version"] == CANONICAL_DOCUMENT_SCHEMA
    assert len(version["document_hash"]) == 64


def test_stable_node_ids_are_preserved_and_duplicates_are_repaired() -> None:
    existing_id = "13a4b02a-4a2e-4a7b-a88e-6e47d6c8184f"
    document = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "attrs": {"nodeId": existing_id}},
            {"type": "paragraph", "attrs": {"nodeId": existing_id}},
            {"type": "blockquote", "content": [{"type": "paragraph"}]},
        ],
    }

    first = ensure_scene_node_ids(document)
    second = ensure_scene_node_ids(first)
    repeated_import = ensure_scene_node_ids(document)
    node_ids = [
        first["content"][0]["attrs"]["nodeId"],
        first["content"][1]["attrs"]["nodeId"],
        first["content"][2]["attrs"]["nodeId"],
        first["content"][2]["content"][0]["attrs"]["nodeId"],
    ]

    assert node_ids[0] == existing_id
    assert len(set(node_ids)) == 4
    assert all(str(UUID(node_id)) == node_id for node_id in node_ids)
    assert second == first
    assert repeated_import == first
    assert document["content"][1]["attrs"]["nodeId"] == existing_id


def test_document_codec_rejects_unsupported_nodes_and_mismatched_projection() -> None:
    with pytest.raises(SceneDocumentError, match="unsupported block node"):
        build_scene_document(
            content_json={"type": "doc", "content": [{"type": "table"}]},
            content_markdown=None,
        )

    with pytest.raises(SceneDocumentError, match="does not match"):
        build_scene_document(
            content_json={
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": "plain"}],
                    }
                ],
            },
            content_markdown="**plain**",
        )


def test_backend_matches_shared_scene_document_contract() -> None:
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "scene-document-v1.json"
    cases = json.loads(contract_path.read_text(encoding="utf-8"))

    for case in cases:
        document = build_scene_document(
            content_json=case["document"],
            content_markdown=case["markdown"],
        )
        assert document.content_markdown == case["markdown"], case["name"]
        assert document.content_text == case["plaintext"], case["name"]


def test_database_allows_review_metadata_but_rejects_document_mutation(
    client: TestClient,
    database_path: Path,
) -> None:
    scene = create_scene(client)
    version = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "Immutable prose."},
        )
    )

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "UPDATE scene_versions SET summary = ? WHERE id = ?",
            ("Allowed review metadata.", version["id"]),
        )
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="scene version document is immutable"):
            connection.execute(
                "UPDATE scene_versions SET content_text = ? WHERE id = ?",
                ("Changed.", version["id"]),
            )
