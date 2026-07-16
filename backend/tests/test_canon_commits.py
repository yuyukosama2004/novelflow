from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete, insert, update
from sqlalchemy.exc import DBAPIError

from app.api import review as review_api
from app.canon.hashing import scene_version_content_hash
from app.models import Base
from app.models.canon import CanonCommit


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_scene(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    project = response_data(client.post("/api/projects", json={"title": "Canon story"}))
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
            json={
                "sequence_no": 1,
                "title": "Scene",
                "goal": "Find the key",
                "must_include_json": ["red key"],
            },
        )
    )
    return project, scene


def create_version(client: TestClient, scene_id: str, text: str) -> dict[str, Any]:
    return response_data(
        client.post(
            f"/api/scenes/{scene_id}/versions",
            json={
                "content_markdown": text,
                "content_json": {
                    "type": "doc",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": text}],
                        }
                    ],
                },
            },
        )
    )


class NoIssueReviewer:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, *_: Any) -> list[Any]:
        return []


def review_and_approve(
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


def test_approval_creates_one_queryable_canon_commit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, scene = create_scene(client)
    version = create_version(client, scene["id"], "The red key turns.")

    review_and_approve(client, monkeypatch, scene["id"], version["id"])
    commits = response_data(client.get(f"/api/scenes/{scene['id']}/canon-commits"))

    assert len(commits) == 1
    commit = commits[0]
    assert commit["project_id"] == project["id"]
    assert commit["scene_version_id"] == version["id"]
    assert commit["previous_commit_id"] is None
    assert commit["sequence_no"] == 1
    assert commit["commit_reason"] == "initial_approval"
    assert commit["contract_snapshot_json"]["goal"] == "Find the key"
    assert commit["contract_snapshot_json"]["must_include"] == ["red key"]
    assert commit["review_snapshot_json"]["status"] == "completed"
    assert commit["content_hash"] == scene_version_content_hash(
        version["content_json"],
        version["content_markdown"],
    )

    response_data(
        client.post(
            f"/api/scenes/{scene['id']}/approve-version",
            json={"version_id": version["id"]},
        )
    )
    repeated = response_data(client.get(f"/api/scenes/{scene['id']}/canon-commits"))
    assert len(repeated) == 1


def test_replacement_appends_to_linear_canon_history(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, scene = create_scene(client)
    first = create_version(client, scene["id"], "First canon.")
    review_and_approve(client, monkeypatch, scene["id"], first["id"])
    second = create_version(client, scene["id"], "Replacement canon.")
    review_and_approve(client, monkeypatch, scene["id"], second["id"])

    commits = response_data(client.get(f"/api/scenes/{scene['id']}/canon-commits"))

    assert [commit["sequence_no"] for commit in commits] == [2, 1]
    assert commits[0]["scene_version_id"] == second["id"]
    assert commits[0]["previous_commit_id"] == commits[1]["id"]
    assert commits[0]["commit_reason"] == "version_replacement"
    assert commits[1]["scene_version_id"] == first["id"]

    repeated_history = client.post(
        f"/api/scenes/{scene['id']}/approve-version",
        json={"version_id": first["id"]},
    )
    refreshed_scene = response_data(client.get(f"/api/scenes/{scene['id']}"))
    unchanged_commits = response_data(client.get(f"/api/scenes/{scene['id']}/canon-commits"))

    assert repeated_history.status_code == 409
    assert repeated_history.json()["details"]["reason"] == "VERSION_ALREADY_COMMITTED"
    assert refreshed_scene["approved_version_id"] == second["id"]
    assert len(unchanged_commits) == 2


def test_markdown_export_reads_latest_canon_when_projection_drifts(
    client: TestClient,
    database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, scene = create_scene(client)
    first = create_version(client, scene["id"], "First canon.")
    review_and_approve(client, monkeypatch, scene["id"], first["id"])
    second = create_version(client, scene["id"], "Second canon.")
    review_and_approve(client, monkeypatch, scene["id"], second["id"])

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "UPDATE scenes SET approved_version_id = ? WHERE id = ?",
            (first["id"], scene["id"]),
        )
        connection.commit()

    exported = client.get(f"/api/projects/{project['id']}/exports/markdown")

    assert exported.status_code == 200
    assert "Second canon." in exported.text
    assert "First canon." not in exported.text


def test_sqlite_rejects_canon_commit_updates_and_deletes(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'immutable.db'}")
    Base.metadata.create_all(engine)
    commit_id = "commit-1"
    values = {
        "id": commit_id,
        "project_id": "project-1",
        "scene_id": "scene-1",
        "scene_version_id": "version-1",
        "previous_commit_id": None,
        "sequence_no": 1,
        "content_hash": "a" * 64,
        "contract_snapshot_json": {},
        "review_snapshot_json": {},
        "commit_reason": "test",
        "override_reason": None,
        "committed_by": "user",
        "committed_at": datetime.now(timezone.utc),
    }
    with engine.begin() as connection:
        connection.execute(insert(CanonCommit).values(**values))

    with pytest.raises(DBAPIError, match="canon commits are immutable"):
        with engine.begin() as connection:
            connection.execute(
                update(CanonCommit).where(CanonCommit.id == commit_id).values(commit_reason="changed")
            )

    with pytest.raises(DBAPIError, match="canon commits are immutable"):
        with engine.begin() as connection:
            connection.execute(delete(CanonCommit).where(CanonCommit.id == commit_id))

    engine.dispose()


def test_integrity_audit_detects_projection_and_content_drift(
    client: TestClient,
    database_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, scene = create_scene(client)
    first = create_version(client, scene["id"], "First canon.")
    review_and_approve(client, monkeypatch, scene["id"], first["id"])
    second = create_version(client, scene["id"], "Second canon.")
    review_and_approve(client, monkeypatch, scene["id"], second["id"])

    healthy = response_data(client.get(f"/api/projects/{project['id']}/canon-integrity"))
    assert healthy["status"] == "ok"
    assert healthy["checked_scenes"] == 1
    assert healthy["checked_commits"] == 2
    assert healthy["issues"] == []

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            "UPDATE scenes SET approved_version_id = ? WHERE id = ?",
            (first["id"], scene["id"]),
        )
        connection.execute("DROP TRIGGER scene_versions_prevent_document_update")
        connection.execute(
            "UPDATE scene_versions SET content_markdown = ? WHERE id = ?",
            ("Tampered after approval.", second["id"]),
        )
        connection.execute(
            """
            INSERT INTO canon_commits (
                id, project_id, scene_id, scene_version_id, previous_commit_id,
                sequence_no, content_hash, contract_snapshot_json,
                review_snapshot_json, commit_reason, override_reason,
                committed_by, committed_at
            ) VALUES (?, ?, ?, ?, NULL, 1, ?, '{}', '{}', ?, NULL, ?, ?)
            """,
            (
                "orphan-commit",
                project["id"],
                "missing-scene",
                "missing-version",
                "b" * 64,
                "test_orphan",
                "test",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()

    drift = response_data(client.get(f"/api/projects/{project['id']}/canon-integrity"))
    issue_codes = {issue["code"] for issue in drift["issues"]}

    assert drift["status"] == "drift"
    assert "PROJECTION_VERSION_MISMATCH" in issue_codes
    assert "DOCUMENT_HASH_MISMATCH" in issue_codes
    assert "COMMIT_HASH_MISMATCH" in issue_codes
    assert "COMMIT_SCENE_MISSING" in issue_codes
