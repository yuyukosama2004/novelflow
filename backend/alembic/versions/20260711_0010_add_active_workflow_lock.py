"""add active workflow lock

Revision ID: 20260711_0010
Revises: 20260711_0009
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0010"
down_revision: str | None = "20260711_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_workflow_active_scene",
        "workflow_runs",
        ["scene_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'planning', 'drafting')"),
    )


def downgrade() -> None:
    op.drop_index("uq_workflow_active_scene", table_name="workflow_runs")
