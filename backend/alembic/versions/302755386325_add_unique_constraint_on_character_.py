"""add unique constraint on character relationships

Revision ID: 302755386325
Revises: bc594df4182d
Create Date: 2026-06-28 22:17:45.308523
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '302755386325'
down_revision: str | None = 'bc594df4182d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('character_relationships') as batch_op:
        batch_op.create_unique_constraint(
            'uq_character_relation',
            ['project_id', 'character_a_id', 'character_b_id', 'relation_type'],
        )


def downgrade() -> None:
    with op.batch_alter_table('character_relationships') as batch_op:
        batch_op.drop_constraint('uq_character_relation', type_='unique')
