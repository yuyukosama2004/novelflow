"""add review runs

Revision ID: 20260711_0001
Revises: ebb576311cf9
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0001"
down_revision: str | None = "ebb576311cf9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_runs",
        sa.Column("scene_version_id", sa.String(length=36), nullable=False),
        sa.Column("model_profile_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("prompt_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_version_id"], ["scene_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_review_runs_scene_version_id"),
        "review_runs",
        ["scene_version_id"],
        unique=False,
    )
    with op.batch_alter_table("review_issues") as batch_op:
        batch_op.add_column(sa.Column("review_run_id", sa.String(length=36), nullable=True))
        batch_op.create_index(
            op.f("ix_review_issues_review_run_id"),
            ["review_run_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_review_issues_review_run_id",
            "review_runs",
            ["review_run_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("review_issues") as batch_op:
        batch_op.drop_constraint("fk_review_issues_review_run_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_review_issues_review_run_id"))
        batch_op.drop_column("review_run_id")
    op.drop_index(op.f("ix_review_runs_scene_version_id"), table_name="review_runs")
    op.drop_table("review_runs")
