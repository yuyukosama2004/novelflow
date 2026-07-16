"""add canonical scene document metadata

Revision ID: 20260716_0002
Revises: 20260716_0001
Create Date: 2026-07-16
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "20260716_0002"
down_revision: str | None = "20260716_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_DOCUMENT_SCHEMA = "novelflow.scene-document.legacy-v1"


def upgrade() -> None:
    op.add_column(
        "scene_versions",
        sa.Column("content_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "scene_versions",
        sa.Column("document_schema_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "scene_versions",
        sa.Column("document_hash", sa.String(length=64), nullable=True),
    )

    _backfill_document_metadata()

    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.alter_column("content_text", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column(
            "document_schema_version",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.alter_column(
            "document_hash",
            existing_type=sa.String(length=64),
            nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_scene_version_document_hash_length",
            "length(document_hash) = 64",
        )
        batch_op.create_check_constraint(
            "ck_scene_version_document_schema",
            "length(document_schema_version) > 0",
        )

    if op.get_bind().dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER scene_versions_prevent_document_update
            BEFORE UPDATE OF
                scene_id,
                version_no,
                parent_version_id,
                branch_name,
                content_json,
                content_markdown,
                content_text,
                document_schema_version,
                document_hash,
                source_type,
                model_profile_id,
                prompt_snapshot_json,
                context_manifest_json,
                created_by
            ON scene_versions
            BEGIN
                SELECT RAISE(ABORT, 'scene version document is immutable');
            END
            """
        )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS scene_versions_prevent_document_update")
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.drop_constraint(
            "ck_scene_version_document_schema",
            type_="check",
        )
        batch_op.drop_constraint(
            "ck_scene_version_document_hash_length",
            type_="check",
        )
        batch_op.drop_column("document_hash")
        batch_op.drop_column("document_schema_version")
        batch_op.drop_column("content_text")


def _backfill_document_metadata() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    versions = sa.Table("scene_versions", metadata, autoload_with=bind)
    rows = bind.execute(
        sa.select(
            versions.c.id,
            versions.c.content_json,
            versions.c.content_markdown,
        )
    ).mappings()
    for row in rows:
        content_json = _json_value(row["content_json"])
        content_markdown = str(row["content_markdown"] or "").replace("\r\n", "\n").replace("\r", "\n")
        bind.execute(
            versions.update()
            .where(versions.c.id == row["id"])
            .values(
                content_text=_collect_text(content_json).strip(),
                document_schema_version=LEGACY_DOCUMENT_SCHEMA,
                document_hash=_content_hash(content_json, content_markdown),
            )
        )


def _content_hash(content_json: dict[str, Any], content_markdown: str) -> str:
    payload = {
        "schema": "novelflow.scene-version.v1",
        "content_json": content_json,
        "content_markdown": content_markdown,
    }
    canonical_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _json_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {"type": "doc", "content": [{"type": "paragraph"}]}
        if isinstance(parsed, dict):
            return parsed
    return {"type": "doc", "content": [{"type": "paragraph"}]}


def _collect_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    text = value.get("text")
    own_text = text if isinstance(text, str) else ""
    children = value.get("content")
    if not isinstance(children, list):
        return own_text
    return own_text + "".join(_collect_text(child) for child in children)
