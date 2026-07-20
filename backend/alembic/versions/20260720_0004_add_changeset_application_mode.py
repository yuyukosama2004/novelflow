"""add change operation application mode

Revision ID: 20260720_0004
Revises: 20260718_0003
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260720_0004"
down_revision: str | None = "20260718_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "change_operations",
        sa.Column(
            "application_mode",
            sa.String(length=40),
            nullable=False,
            server_default="",
        ),
    )


def downgrade() -> None:
    op.drop_column("change_operations", "application_mode")
