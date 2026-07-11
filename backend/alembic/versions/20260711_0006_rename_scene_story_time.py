"""rename scene timeline order to story time order

Revision ID: 20260711_0006
Revises: 20260711_0005
Create Date: 2026-07-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260711_0006"
down_revision: str | None = "20260711_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.alter_column(
            "timeline_order",
            new_column_name="story_time_order",
        )


def downgrade() -> None:
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.alter_column(
            "story_time_order",
            new_column_name="timeline_order",
        )
