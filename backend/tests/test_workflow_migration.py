from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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


def seed_scene(database_path: Path) -> None:
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with Session(engine) as session:
        project = NovelProject(id="project-1", title="Legacy workflow")
        volume = Volume(
            id="volume-1",
            project=project,
            sequence_no=1,
            title="Volume",
        )
        chapter = Chapter(
            id="chapter-1",
            volume=volume,
            sequence_no=1,
            title="Chapter",
        )
        session.add(
            Scene(
                id="scene-1",
                chapter=chapter,
                sequence_no=1,
                title="Scene",
            )
        )
        session.commit()
    engine.dispose()


def test_migration_preserves_existing_workflow_runs(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy-workflow.db"
    run_alembic(database_path, "upgrade", "20260716_0002")
    seed_scene(database_path)
    now = datetime.now(timezone.utc).isoformat()
    existing_events = [{"event_id": 1, "event": "version_created"}]
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            INSERT INTO workflow_runs (
                scene_id, model_profile_id, run_type, status, provider, model,
                plan, draft, final_content, prompt_snapshot_json,
                context_manifest_json, events_json, error, version_created_id,
                id, created_at, updated_at
            ) VALUES (
                'scene-1', NULL, 'scene_writing', 'waiting_review', 'fake', 'fake',
                'plan', 'draft', 'draft', '{}', '{}', ?, '', NULL,
                'workflow-1', ?, ?
            )
            """,
            (json.dumps(existing_events), now, now),
        )
        connection.commit()

    run_alembic(database_path, "upgrade", "head")

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT status, draft, events_json, idempotency_key, input_hash,
                   attempt, current_step_key, lease_owner
            FROM workflow_runs
            WHERE id = 'workflow-1'
            """
        ).fetchone()
        assert row is not None
        assert row["status"] == "waiting_review"
        assert row["draft"] == "draft"
        assert json.loads(row["events_json"]) == existing_events
        assert row["idempotency_key"] is None
        assert row["input_hash"] == ""
        assert row["attempt"] == 0
        assert row["current_step_key"] == ""
        assert row["lease_owner"] == ""
        tables = {
            value[0]
            for value in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        assert {"workflow_step_runs", "workflow_events"} <= tables

    run_alembic(database_path, "downgrade", "20260716_0002")
    with closing(sqlite3.connect(database_path)) as connection:
        row = connection.execute("SELECT status, draft FROM workflow_runs WHERE id = 'workflow-1'").fetchone()
        assert row == ("waiting_review", "draft")
    run_alembic(database_path, "upgrade", "head")
