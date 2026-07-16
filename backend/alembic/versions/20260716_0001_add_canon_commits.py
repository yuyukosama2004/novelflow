"""add immutable canon commit ledger

Revision ID: 20260716_0001
Revises: 20260711_0011
Create Date: 2026-07-16
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import sqlalchemy as sa

from alembic import op

revision: str = "20260716_0001"
down_revision: str | None = "20260711_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "canon_commits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("scene_version_id", sa.String(length=36), nullable=False),
        sa.Column("previous_commit_id", sa.String(length=36), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("contract_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("review_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("commit_reason", sa.String(length=40), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("committed_by", sa.String(length=80), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(content_hash) = 64",
            name="ck_canon_commit_hash_length",
        ),
        sa.CheckConstraint(
            "sequence_no > 0",
            name="ck_canon_commit_positive_sequence",
        ),
        sa.ForeignKeyConstraint(["previous_commit_id"], ["canon_commits.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["novel_projects.id"]),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"]),
        sa.ForeignKeyConstraint(["scene_version_id"], ["scene_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scene_id",
            "sequence_no",
            name="uq_canon_commit_scene_sequence",
        ),
        sa.UniqueConstraint(
            "scene_version_id",
            name="uq_canon_commit_scene_version",
        ),
    )
    op.create_index(
        op.f("ix_canon_commits_previous_commit_id"),
        "canon_commits",
        ["previous_commit_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canon_commits_project_id"),
        "canon_commits",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canon_commits_scene_id"),
        "canon_commits",
        ["scene_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_canon_commits_scene_version_id"),
        "canon_commits",
        ["scene_version_id"],
        unique=False,
    )

    _backfill_existing_approvals()

    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER canon_commits_prevent_update
            BEFORE UPDATE ON canon_commits
            BEGIN
                SELECT RAISE(ABORT, 'canon commits are immutable');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER canon_commits_prevent_delete
            BEFORE DELETE ON canon_commits
            BEGIN
                SELECT RAISE(ABORT, 'canon commits are immutable');
            END
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS canon_commits_prevent_delete")
        op.execute("DROP TRIGGER IF EXISTS canon_commits_prevent_update")
    op.drop_index(op.f("ix_canon_commits_scene_version_id"), table_name="canon_commits")
    op.drop_index(op.f("ix_canon_commits_scene_id"), table_name="canon_commits")
    op.drop_index(op.f("ix_canon_commits_project_id"), table_name="canon_commits")
    op.drop_index(op.f("ix_canon_commits_previous_commit_id"), table_name="canon_commits")
    op.drop_table("canon_commits")


def _backfill_existing_approvals() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    scenes = sa.Table("scenes", metadata, autoload_with=bind)
    chapters = sa.Table("chapters", metadata, autoload_with=bind)
    volumes = sa.Table("volumes", metadata, autoload_with=bind)
    versions = sa.Table("scene_versions", metadata, autoload_with=bind)
    commits = sa.Table("canon_commits", metadata, autoload_with=bind)

    rows = bind.execute(
        sa.select(
            scenes.c.id.label("scene_id"),
            scenes.c.approved_version_id,
            scenes.c.goal,
            scenes.c.conflict,
            scenes.c.turning_point,
            scenes.c.ending_hook,
            scenes.c.pov_character_id,
            scenes.c.location_id,
            scenes.c.time_text,
            scenes.c.story_time_order,
            scenes.c.must_include_json,
            scenes.c.must_not_reveal_json,
            scenes.c.forbidden_actions_json,
            volumes.c.project_id,
            versions.c.id.label("version_id"),
            versions.c.version_no,
            versions.c.content_json,
            versions.c.content_markdown,
            versions.c.created_by,
            versions.c.approved_at,
            versions.c.superseded_at,
            versions.c.approval_override_reason,
        )
        .select_from(
            scenes.join(chapters, scenes.c.chapter_id == chapters.c.id)
            .join(volumes, chapters.c.volume_id == volumes.c.id)
            .join(versions, versions.c.scene_id == scenes.c.id)
        )
        .where(
            sa.or_(
                versions.c.approved_at.is_not(None),
                versions.c.superseded_at.is_not(None),
                versions.c.id == scenes.c.approved_version_id,
            )
        )
        .order_by(
            scenes.c.id,
            versions.c.approved_at,
            versions.c.version_no,
            versions.c.id,
        )
    ).mappings()

    by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scene[str(row["scene_id"])].append(dict(row))

    for scene_rows in by_scene.values():
        current_version_id = scene_rows[0]["approved_version_id"]
        historical_rows = [row for row in scene_rows if row["version_id"] != current_version_id]
        current_rows = [row for row in scene_rows if row["version_id"] == current_version_id]
        ordered_rows = historical_rows + current_rows
        previous_commit_id: str | None = None

        for sequence_no, row in enumerate(ordered_rows, start=1):
            commit_id = str(uuid4())
            bind.execute(
                commits.insert().values(
                    id=commit_id,
                    project_id=row["project_id"],
                    scene_id=row["scene_id"],
                    scene_version_id=row["version_id"],
                    previous_commit_id=previous_commit_id,
                    sequence_no=sequence_no,
                    content_hash=_content_hash(
                        _json_value(row["content_json"], {}),
                        str(row["content_markdown"] or ""),
                    ),
                    contract_snapshot_json=_contract_snapshot(row),
                    review_snapshot_json={
                        "source": "migration_backfill",
                        "review_run_id": None,
                        "issues": [],
                    },
                    commit_reason="migration_backfill",
                    override_reason=row["approval_override_reason"],
                    committed_by=str(row["created_by"] or "user"),
                    committed_at=(row["approved_at"] or row["superseded_at"] or datetime.now(timezone.utc)),
                )
            )
            previous_commit_id = commit_id


def _content_hash(content_json: dict[str, Any], content_markdown: str) -> str:
    payload = {
        "schema": "novelflow.scene-version.v1",
        "content_json": content_json,
        "content_markdown": content_markdown.replace("\r\n", "\n").replace("\r", "\n"),
    }
    canonical_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _contract_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_source": "migration_current_scene",
        "goal": row["goal"] or "",
        "conflict": row["conflict"] or "",
        "turning_point": row["turning_point"] or "",
        "ending_hook": row["ending_hook"] or "",
        "pov_character_id": row["pov_character_id"],
        "location_id": row["location_id"],
        "time_text": row["time_text"] or "",
        "story_time_order": row["story_time_order"],
        "must_include": _json_value(row["must_include_json"], []),
        "must_not_reveal": _json_value(row["must_not_reveal_json"], []),
        "forbidden_actions": _json_value(row["forbidden_actions_json"], []),
    }


def _json_value(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return value
