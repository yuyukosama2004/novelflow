"""add approval gate fields

Revision ID: 20260711_0002
Revises: 20260711_0001
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0002"
down_revision: str | None = "20260711_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.add_column(sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("approval_override_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.drop_column("approval_override_reason")
        batch_op.drop_column("approved_at")
