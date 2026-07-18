"""add workflow event cursor

Revision ID: 20260718_0002
Revises: 20260718_0001
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0002"
down_revision: str | None = "20260718_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(
            sa.Column(
                "last_event_sequence",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
    op.execute(
        """
        UPDATE workflow_runs
        SET last_event_sequence = COALESCE(
            (
                SELECT MAX(workflow_events.sequence_no)
                FROM workflow_events
                WHERE workflow_events.workflow_run_id = workflow_runs.id
            ),
            0
        )
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("last_event_sequence")
