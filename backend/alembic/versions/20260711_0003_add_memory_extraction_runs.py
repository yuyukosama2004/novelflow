"""add memory extraction runs

Revision ID: 20260711_0003
Revises: 20260711_0002
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0003"
down_revision: str | None = "20260711_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_extraction_runs",
        sa.Column("scene_version_id", sa.String(length=36), nullable=False),
        sa.Column("model_profile_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("prompt_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_version_id"], ["scene_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_memory_extraction_runs_scene_version_id"),
        "memory_extraction_runs",
        ["scene_version_id"],
        unique=False,
    )
    with op.batch_alter_table("memory_candidates") as batch_op:
        batch_op.add_column(sa.Column("extraction_run_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            op.f("ix_memory_candidates_extraction_run_id"),
            ["extraction_run_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_memory_candidates_extraction_run_id",
            "memory_extraction_runs",
            ["extraction_run_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("memory_candidates") as batch_op:
        batch_op.drop_constraint("fk_memory_candidates_extraction_run_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_memory_candidates_extraction_run_id"))
        batch_op.drop_column("extraction_run_id")
    op.drop_index(
        op.f("ix_memory_extraction_runs_scene_version_id"),
        table_name="memory_extraction_runs",
    )
    op.drop_table("memory_extraction_runs")
