"""add chunk evidence positions

Revision ID: 20260711_0008
Revises: 20260711_0007
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0008"
down_revision: str | None = "20260711_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("review_issues", "memory_candidates"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(
                sa.Column("source_chunk_index", sa.Integer(), nullable=False, server_default="0")
            )
            batch_op.add_column(sa.Column("source_start", sa.Integer(), nullable=False, server_default="0"))
            batch_op.add_column(sa.Column("source_end", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for table_name in ("memory_candidates", "review_issues"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("source_end")
            batch_op.drop_column("source_start")
            batch_op.drop_column("source_chunk_index")
