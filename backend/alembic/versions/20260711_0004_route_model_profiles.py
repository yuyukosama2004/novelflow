"""route model profiles through generation operations

Revision ID: 20260711_0004
Revises: 20260711_0003
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0004"
down_revision: str | None = "20260711_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("novel_projects") as batch_op:
        batch_op.add_column(sa.Column("default_model_profile_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_novel_projects_default_model_profile_id",
            "model_profiles",
            ["default_model_profile_id"],
            ["id"],
        )

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("model_profile_id", sa.String(length=36), nullable=True))

    for table_name in ("review_runs", "memory_extraction_runs"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column("provider", sa.String(length=40), nullable=False, server_default="")
            )
            batch_op.add_column(sa.Column("model", sa.String(length=100), nullable=False, server_default=""))

    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.add_column(sa.Column("model_profile_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("provider", sa.String(length=40), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("model", sa.String(length=100), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("interview_sessions") as batch_op:
        batch_op.drop_column("model")
        batch_op.drop_column("provider")
        batch_op.drop_column("model_profile_id")

    for table_name in ("memory_extraction_runs", "review_runs"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("model")
            batch_op.drop_column("provider")

    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("model_profile_id")

    with op.batch_alter_table("novel_projects") as batch_op:
        batch_op.drop_constraint(
            "fk_novel_projects_default_model_profile_id",
            type_="foreignkey",
        )
        batch_op.drop_column("default_model_profile_id")
