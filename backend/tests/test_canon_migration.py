from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.canon.hashing import scene_version_content_hash
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
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


def seed_approved_history(database_path: Path) -> tuple[SceneVersion, SceneVersion]:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    second_time = datetime.now(timezone.utc)
    first = SceneVersion(
        id="version-1",
        scene_id="scene-1",
        version_no=1,
        content_json={
            "type": "doc",
            "content": [{"type": "paragraph", "content": [{"type": "text", "text": "First"}]}],
        },
        content_markdown="First",
        superseded_at=second_time,
        superseded_by_version_id="version-2",
    )
    second = SceneVersion(
        id="version-2",
        scene_id="scene-1",
        version_no=2,
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
        session.add_all([first, second])
        session.commit()
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
        assert len(commits) == 2
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

    run_alembic(database_path, "downgrade", "20260711_0011")
    run_alembic(database_path, "upgrade", "head")

    with closing(sqlite3.connect(database_path)) as connection:
        count = connection.execute("SELECT COUNT(*) FROM canon_commits").fetchone()
    assert count == (2,)
