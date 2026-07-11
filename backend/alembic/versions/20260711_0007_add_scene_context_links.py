"""add scene context links and knowledge lifecycle

Revision ID: 20260711_0007
Revises: 20260711_0006
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0007"
down_revision: str | None = "20260711_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("character_knowledge") as batch_op:
        batch_op.add_column(
            sa.Column(
                "record_status",
                sa.String(length=40),
                nullable=False,
                server_default="active",
            )
        )

    op.create_table(
        "scene_characters",
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("character_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_id", "character_id", name="uq_scene_character"),
    )
    op.create_index(
        op.f("ix_scene_characters_scene_id"),
        "scene_characters",
        ["scene_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scene_characters_character_id"),
        "scene_characters",
        ["character_id"],
        unique=False,
    )

    op.create_table(
        "scene_world_entries",
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("world_entry_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"]),
        sa.ForeignKeyConstraint(["world_entry_id"], ["world_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_id", "world_entry_id", name="uq_scene_world_entry"),
    )
    op.create_index(
        op.f("ix_scene_world_entries_scene_id"),
        "scene_world_entries",
        ["scene_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scene_world_entries_world_entry_id"),
        "scene_world_entries",
        ["world_entry_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_scene_world_entries_world_entry_id"),
        table_name="scene_world_entries",
    )
    op.drop_index(
        op.f("ix_scene_world_entries_scene_id"),
        table_name="scene_world_entries",
    )
    op.drop_table("scene_world_entries")
    op.drop_index(
        op.f("ix_scene_characters_character_id"),
        table_name="scene_characters",
    )
    op.drop_index(
        op.f("ix_scene_characters_scene_id"),
        table_name="scene_characters",
    )
    op.drop_table("scene_characters")
    with op.batch_alter_table("character_knowledge") as batch_op:
        batch_op.drop_column("record_status")
