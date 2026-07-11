from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_project_scene(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    project = response_data(client.post("/api/projects", json={"title": "Context story"}))
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
    return project, scene


def create_character(client: TestClient, project_id: str, name: str) -> dict[str, Any]:
    return response_data(
        client.post(
            f"/api/projects/{project_id}/characters",
            json={"name": name},
        )
    )


def create_approved_world(
    client: TestClient,
    project_id: str,
    name: str,
    entry_type: str,
) -> dict[str, Any]:
    entry = response_data(
        client.post(
            f"/api/projects/{project_id}/world-entries",
            json={"name": name, "entry_type": entry_type},
        )
    )
    return response_data(client.post(f"/api/world-entries/{entry['id']}/approve"))


def test_context_uses_pov_explicit_links_and_project_rules(client: TestClient) -> None:
    project, scene = create_project_scene(client)
    pov = create_character(client, project["id"], "POV")
    linked = create_character(client, project["id"], "Linked")
    custom = create_approved_world(client, project["id"], "Linked place", "location")
    rule = create_approved_world(client, project["id"], "Hard rule", "rule")
    response_data(
        client.patch(
            f"/api/scenes/{scene['id']}",
            json={"pov_character_id": pov["id"]},
        )
    )

    initial = response_data(client.get(f"/api/scenes/{scene['id']}/context"))
    assert [item["id"] for item in initial["characters"]] == [pov["id"]]
    assert [item["id"] for item in initial["world_facts"]] == [rule["id"]]

    links = response_data(
        client.put(
            f"/api/scenes/{scene['id']}/context-links",
            json={
                "character_ids": [linked["id"]],
                "world_entry_ids": [custom["id"]],
            },
        )
    )
    context = response_data(client.get(f"/api/scenes/{scene['id']}/context"))

    assert links == {
        "character_ids": [linked["id"]],
        "world_entry_ids": [custom["id"]],
    }
    assert {item["id"] for item in context["characters"]} == {pov["id"], linked["id"]}
    assert {item["id"] for item in context["world_facts"]} == {custom["id"], rule["id"]}


def test_context_links_reject_entities_from_another_project(client: TestClient) -> None:
    _, scene = create_project_scene(client)
    other_project = response_data(client.post("/api/projects", json={"title": "Other"}))
    outsider = create_character(client, other_project["id"], "Outsider")

    response = client.put(
        f"/api/scenes/{scene['id']}/context-links",
        json={"character_ids": [outsider["id"]], "world_entry_ids": []},
    )

    assert response.status_code == 422
    assert response.json()["details"]["reason"] == "CONTEXT_LINK_PROJECT_MISMATCH"
