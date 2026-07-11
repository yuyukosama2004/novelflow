"""add working drafts and structured scene content

Revision ID: 20260711_0005
Revises: 20260711_0004
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0005"
down_revision: str | None = "20260711_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "content_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            )
        )

    op.create_table(
        "scene_working_drafts",
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scene_id"),
    )
    op.create_index(
        op.f("ix_scene_working_drafts_scene_id"),
        "scene_working_drafts",
        ["scene_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_scene_working_drafts_scene_id"),
        table_name="scene_working_drafts",
    )
    op.drop_table("scene_working_drafts")
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.drop_column("content_json")
