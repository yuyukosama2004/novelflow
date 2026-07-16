from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.canon.hashing import scene_version_content_hash
from app.models.manuscript import Chapter, Scene, Volume
from app.models.project import NovelProject


def run_alembic(database_path: Path, *arguments: str) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


@dataclass(frozen=True)
class LegacyVersion:
    id: str
    content_json: dict[str, object]
    content_markdown: str


def seed_approved_history(database_path: Path) -> tuple[LegacyVersion, LegacyVersion]:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    second_time = datetime.now(timezone.utc)
    first = LegacyVersion(
        id="version-1",
        content_json={
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "First"}]}],
        },
        content_markdown="First",
    )
    second = LegacyVersion(
        id="version-2",
        content_json={
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Second"}]}],
        },
        content_markdown="Second",
    )
    with Session(engine, expire_on_commit=False) as session:
        session.add(
            NovelProject(
                id="project-1",
                title="Migrated project",
            )
        )
        session.add(
            Volume(
                id="volume-1",
                project_id="project-1",
                sequence_no=1,
                title="Volume",
            )
        )
        session.add(
            Chapter(
                id="chapter-1",
                volume_id="volume-1",
                sequence_no=1,
                title="Chapter",
            )
        )
        session.add(
            Scene(
                id="scene-1",
                chapter_id="chapter-1",
                sequence_no=1,
                title="Scene",
                goal="Preserve history",
                must_include_json=["evidence"],
                approved_version_id=second.id,
            )
        )
        session.commit()
    now = datetime.now(timezone.utc).isoformat()
    with closing(sqlite3.connect(database_path)) as connection:
        connection.executemany(
            """
            INSERT INTO scene_versions (
                id, scene_id, version_no, parent_version_id, branch_name,
                content_json, content_markdown, summary, source_type,
                model_profile_id, prompt_snapshot_json, context_manifest_json,
                review_status, created_by, approved_at,
                approval_override_reason, superseded_at,
                superseded_by_version_id, created_at, updated_at
            ) VALUES (
                ?, 'scene-1', ?, NULL, 'main', ?, ?, '', 'human',
                NULL, '{}', '{}', 'not_reviewed', 'user', NULL,
                NULL, ?, ?, ?, ?
            )
            """,
            [
                (
                    first.id,
                    1,
                    json.dumps(first.content_json),
                    first.content_markdown,
                    second_time.isoformat(),
                    second.id,
                    now,
                    now,
                ),
                (
                    second.id,
                    2,
                    json.dumps(second.content_json),
                    second.content_markdown,
                    None,
                    None,
                    now,
                    now,
                ),
            ],
        )
        connection.commit()
    engine.dispose()
    return first, second


def test_migration_backfills_approved_history_and_is_repeatable(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    run_alembic(database_path, "upgrade", "20260711_0011")
    first, second = seed_approved_history(database_path)

    run_alembic(database_path, "upgrade", "head")

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        commits = connection.execute(
            """
            SELECT id, scene_version_id, previous_commit_id, sequence_no,
                   content_hash, contract_snapshot_json, commit_reason
            FROM canon_commits
            ORDER BY sequence_no
            """
        ).fetchall()
        versions = connection.execute(
            """
            SELECT id, content_text, document_schema_version, document_hash
            FROM scene_versions
            ORDER BY version_no
            """
        ).fetchall()
        assert len(commits) == 2
        assert [row["content_text"] for row in versions] == ["First", "Second"]
        assert {row["document_schema_version"] for row in versions} == {"novelflow.scene-document.legacy-v1"}
        assert [row["document_hash"] for row in versions] == [
            commits[0]["content_hash"],
            commits[1]["content_hash"],
        ]
        assert commits[0]["scene_version_id"] == first.id
        assert commits[0]["previous_commit_id"] is None
        assert commits[1]["scene_version_id"] == second.id
        assert commits[1]["previous_commit_id"] == commits[0]["id"]
        assert [row["sequence_no"] for row in commits] == [1, 2]
        assert commits[0]["content_hash"] == scene_version_content_hash(
            first.content_json,
            first.content_markdown,
        )
        assert commits[1]["content_hash"] == scene_version_content_hash(
            second.content_json,
            second.content_markdown,
        )
        assert commits[1]["commit_reason"] == "migration_backfill"
        assert "migration_current_scene" in commits[1]["contract_snapshot_json"]

        try:
            connection.execute("UPDATE canon_commits SET commit_reason = 'changed' WHERE sequence_no = 1")
        except sqlite3.IntegrityError as exc:
            assert "canon commits are immutable" in str(exc)
        else:  # pragma: no cover - protects the database-level invariant
            raise AssertionError("canon commit update unexpectedly succeeded")
        try:
            connection.execute(
                "UPDATE scene_versions SET content_markdown = 'changed' WHERE id = 'version-1'"
            )
        except sqlite3.IntegrityError as exc:
            assert "scene version document is immutable" in str(exc)
        else:  # pragma: no cover - protects the database-level invariant
            raise AssertionError("scene version document update unexpectedly succeeded")

    run_alembic(database_path, "downgrade", "20260711_0011")
    run_alembic(database_path, "upgrade", "head")

    with closing(sqlite3.connect(database_path)) as connection:
        count = connection.execute("SELECT COUNT(*) FROM canon_commits").fetchone()
    assert count == (2,)
