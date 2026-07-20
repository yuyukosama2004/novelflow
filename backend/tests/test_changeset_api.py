from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.documents.codec import scene_node_hash


def data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_scene(client: TestClient) -> dict[str, Any]:
    project = data(client.post("/api/projects", json={"title": "Change set story"}))
    volume = data(
        client.post(
            f"/api/projects/{project['id']}/volumes",
            json={"sequence_no": 1, "title": "Volume"},
        )
    )
    chapter = data(
        client.post(
            f"/api/volumes/{volume['id']}/chapters",
            json={"sequence_no": 1, "title": "Chapter"},
        )
    )
    return data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 1, "title": "Scene"},
        )
    )


def test_create_and_partially_apply_change_set_to_working_draft(
    client: TestClient,
) -> None:
    scene = create_scene(client)
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "first\n\nsecond"},
        )
    )
    first, second = version["content_json"]["content"]
    change_set = data(
        client.post(
            f"/api/scenes/{scene['id']}/change-sets",
            json={
                "base_working_revision": 0,
                "base_version_id": version["id"],
                "expected_base_document_hash": version["document_hash"],
                "purpose": "rewrite",
                "summary": "Replace first and optionally append.",
                "operations": [
                    {
                        "sequence_no": 1,
                        "operation_type": "replace_block",
                        "target_node_id": first["attrs"]["nodeId"],
                        "original_json": first,
                        "original_hash": scene_node_hash(first),
                        "proposed_json": {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "replaced"}],
                        },
                    },
                    {
                        "sequence_no": 2,
                        "operation_type": "insert_after",
                        "anchor_before_node_id": second["attrs"]["nodeId"],
                        "proposed_json": {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "inserted"}],
                        },
                    },
                ],
            },
        )
    )
    operation_ids = [item["id"] for item in change_set["operations"]]

    applied = data(
        client.post(
            f"/api/change-sets/{change_set['id']}/apply",
            json={
                "expected_draft_revision": 0,
                "accept_operation_ids": [operation_ids[0]],
                "reject_operation_ids": [operation_ids[1]],
            },
        )
    )
    versions = data(client.get(f"/api/scenes/{scene['id']}/versions"))

    assert applied["draft"]["revision"] == 1
    assert applied["draft"]["content_markdown"] == "replaced\n\nsecond"
    assert applied["change_set"]["status"] == "accepted"
    assert [item["status"] for item in applied["change_set"]["operations"]] == [
        "accepted",
        "rejected",
    ]
    assert applied["change_set"]["operations"][0]["accepted_draft_revision"] == 1
    assert applied["change_set"]["operations"][0]["application_mode"] == "direct"
    assert applied["change_set"]["operations"][1]["application_mode"] == ""
    assert len(versions) == 1


def test_change_set_creation_rejects_stale_base_hash(client: TestClient) -> None:
    scene = create_scene(client)
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "baseline"},
        )
    )
    response = client.post(
        f"/api/scenes/{scene['id']}/change-sets",
        json={
            "base_working_revision": 0,
            "base_version_id": version["id"],
            "expected_base_document_hash": "0" * 64,
            "purpose": "rewrite",
            "operations": [
                {
                    "sequence_no": 1,
                    "operation_type": "delete_block",
                    "target_node_id": version["content_json"]["content"][0]["attrs"]["nodeId"],
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["details"]["reason"] == "BASE_DOCUMENT_HASH_MISMATCH"


def test_rejecting_all_operations_does_not_create_or_advance_a_draft(
    client: TestClient,
) -> None:
    scene = create_scene(client)
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "baseline"},
        )
    )
    block = version["content_json"]["content"][0]
    change_set = data(
        client.post(
            f"/api/scenes/{scene['id']}/change-sets",
            json={
                "base_working_revision": 0,
                "base_version_id": version["id"],
                "purpose": "rewrite",
                "operations": [
                    {
                        "sequence_no": 1,
                        "operation_type": "delete_block",
                        "target_node_id": block["attrs"]["nodeId"],
                        "original_hash": scene_node_hash(block),
                    }
                ],
            },
        )
    )

    result = data(
        client.post(
            f"/api/change-sets/{change_set['id']}/apply",
            json={
                "expected_draft_revision": 0,
                "reject_operation_ids": [change_set["operations"][0]["id"]],
            },
        )
    )
    draft = data(client.get(f"/api/scenes/{scene['id']}/working-draft"))

    assert result["change_set"]["status"] == "rejected"
    assert result["draft"] is None
    assert draft["revision"] == 0


def test_pending_operation_rebases_after_an_earlier_partial_accept(
    client: TestClient,
) -> None:
    scene = create_scene(client)
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "first\n\nsecond"},
        )
    )
    first, second = version["content_json"]["content"]
    operations = []
    for sequence_no, block, replacement in (
        (1, first, "first changed"),
        (2, second, "second changed"),
    ):
        operations.append(
            {
                "sequence_no": sequence_no,
                "operation_type": "replace_block",
                "target_node_id": block["attrs"]["nodeId"],
                "original_hash": scene_node_hash(block),
                "proposed_json": {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": replacement}],
                },
            }
        )
    change_set = data(
        client.post(
            f"/api/scenes/{scene['id']}/change-sets",
            json={
                "base_working_revision": 0,
                "base_version_id": version["id"],
                "purpose": "rewrite",
                "operations": operations,
            },
        )
    )
    first_id, second_id = [item["id"] for item in change_set["operations"]]

    first_apply = data(
        client.post(
            f"/api/change-sets/{change_set['id']}/apply",
            json={"expected_draft_revision": 0, "accept_operation_ids": [first_id]},
        )
    )
    stale = client.post(
        f"/api/change-sets/{change_set['id']}/apply",
        json={"expected_draft_revision": 0, "accept_operation_ids": [second_id]},
    )
    rebased = data(
        client.post(
            f"/api/change-sets/{change_set['id']}/apply",
            json={"expected_draft_revision": 1, "accept_operation_ids": [second_id]},
        )
    )

    assert first_apply["change_set"]["status"] == "partially_accepted"
    assert stale.status_code == 409
    assert stale.json()["details"]["current_revision"] == 1
    assert rebased["draft"]["revision"] == 2
    assert rebased["draft"]["content_markdown"] == "first changed\n\nsecond changed"
    assert rebased["change_set"]["status"] == "accepted"
    assert rebased["change_set"]["operations"][0]["application_mode"] == "direct"
    assert rebased["change_set"]["operations"][1]["application_mode"] == "rebased"


def test_three_way_merges_non_overlapping_author_edit(client: TestClient) -> None:
    scene = create_scene(client)
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "The lantern went dark."},
        )
    )
    block = version["content_json"]["content"][0]
    change_set = data(
        client.post(
            f"/api/scenes/{scene['id']}/change-sets",
            json={
                "base_working_revision": 0,
                "base_version_id": version["id"],
                "purpose": "rewrite",
                "operations": [
                    {
                        "sequence_no": 1,
                        "operation_type": "replace_block",
                        "target_node_id": block["attrs"]["nodeId"],
                        "original_json": block,
                        "original_hash": scene_node_hash(block),
                        "proposed_json": {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "The lantern went completely dark.",
                                }
                            ],
                        },
                    }
                ],
            },
        )
    )
    edited_block = {
        **block,
        "content": [
            {
                "type": "text",
                "text": "Suddenly, the lantern went dark.",
            }
        ],
    }
    draft = data(
        client.put(
            f"/api/scenes/{scene['id']}/working-draft",
            json={
                "revision": 0,
                "content_json": {"type": "doc", "content": [edited_block]},
                "content_markdown": "Suddenly, the lantern went dark.",
            },
        )
    )

    applied = data(
        client.post(
            f"/api/change-sets/{change_set['id']}/apply",
            json={
                "expected_draft_revision": draft["revision"],
                "accept_operation_ids": [change_set["operations"][0]["id"]],
            },
        )
    )

    assert applied["draft"]["revision"] == 2
    assert applied["draft"]["content_markdown"] == "Suddenly, the lantern went completely dark."
    operation = applied["change_set"]["operations"][0]
    assert operation["status"] == "accepted"
    assert operation["application_mode"] == "three_way"
    assert operation["conflict_reason"] == ""


def test_accept_reevaluates_remaining_operations(client: TestClient) -> None:
    scene = create_scene(client)
    version = data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "first\n\nsecond"},
        )
    )
    first = version["content_json"]["content"][0]
    change_set = data(
        client.post(
            f"/api/scenes/{scene['id']}/change-sets",
            json={
                "base_working_revision": 0,
                "base_version_id": version["id"],
                "purpose": "rewrite",
                "operations": [
                    {
                        "sequence_no": 1,
                        "operation_type": "insert_after",
                        "anchor_before_node_id": first["attrs"]["nodeId"],
                        "proposed_json": {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "after first"}],
                        },
                    },
                    {
                        "sequence_no": 2,
                        "operation_type": "delete_block",
                        "target_node_id": first["attrs"]["nodeId"],
                        "original_json": first,
                        "original_hash": scene_node_hash(first),
                    },
                ],
            },
        )
    )

    applied = data(
        client.post(
            f"/api/change-sets/{change_set['id']}/apply",
            json={
                "expected_draft_revision": 0,
                "accept_operation_ids": [change_set["operations"][1]["id"]],
            },
        )
    )

    assert applied["change_set"]["status"] == "conflicted"
    assert [(item["status"], item["conflict_reason"]) for item in applied["change_set"]["operations"]] == [
        ("orphaned", "ANCHOR_NODE_NOT_FOUND"),
        ("accepted", ""),
    ]
