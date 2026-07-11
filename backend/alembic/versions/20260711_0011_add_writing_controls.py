"""add writing controls

Revision ID: 20260711_0011
Revises: 20260711_0010
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0011"
down_revision: str | None = "20260711_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "novel_projects",
        sa.Column(
            "writing_style_preset",
            sa.String(length=40),
            nullable=False,
            server_default="general_web",
        ),
    )
    op.execute("UPDATE novel_projects SET pov_type = 'first_person' WHERE pov_type = '第一人称'")
    op.execute(
        "UPDATE novel_projects SET pov_type = 'third_person_omniscient' WHERE pov_type = '第三人称全知'"
    )
    op.execute(
        "UPDATE novel_projects SET pov_type = 'third_person_limited' "
        "WHERE pov_type = '' OR pov_type = '第三人称限知'"
    )
    op.add_column(
        "novel_projects",
        sa.Column("writing_style_custom", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "novel_projects",
        sa.Column(
            "default_scene_word_count",
            sa.Integer(),
            nullable=False,
            server_default="1000",
        ),
    )


def downgrade() -> None:
    op.drop_column("novel_projects", "default_scene_word_count")
    op.drop_column("novel_projects", "writing_style_custom")
    op.drop_column("novel_projects", "writing_style_preset")
