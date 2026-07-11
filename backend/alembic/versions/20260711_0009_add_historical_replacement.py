"""add historical replacement and impact tracking

Revision ID: 20260711_0009
Revises: 20260711_0008
Create Date: 2026-07-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260711_0009"
down_revision: str | None = "20260711_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.add_column(sa.Column("is_stale", sa.Boolean(), nullable=False, server_default="0"))
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.add_column(sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("superseded_by_version_id", sa.String(36), nullable=True))
    for table_name in ("character_states", "character_knowledge", "timeline_events"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("source_candidate_id", sa.String(36), nullable=True))
    with op.batch_alter_table("timeline_events") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(40), nullable=False, server_default="active"))
    for table_name in ("character_relationships", "world_entries"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(sa.Column("source_scene_version_id", sa.String(36), nullable=True))
            batch_op.add_column(sa.Column("source_candidate_id", sa.String(36), nullable=True))
    op.create_table(
        "impact_reports",
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("source_scene_id", sa.String(36), nullable=False),
        sa.Column("old_version_id", sa.String(36), nullable=False),
        sa.Column("new_version_id", sa.String(36), nullable=False),
        sa.Column("affected_scene_ids_json", sa.JSON(), nullable=False),
        sa.Column("reason_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["novel_projects.id"]),
        sa.ForeignKeyConstraint(["source_scene_id"], ["scenes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_impact_reports_project_id"), "impact_reports", ["project_id"])
    op.create_index(op.f("ix_impact_reports_source_scene_id"), "impact_reports", ["source_scene_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_impact_reports_source_scene_id"), table_name="impact_reports")
    op.drop_index(op.f("ix_impact_reports_project_id"), table_name="impact_reports")
    op.drop_table("impact_reports")
    for table_name in ("world_entries", "character_relationships"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("source_candidate_id")
            batch_op.drop_column("source_scene_version_id")
    with op.batch_alter_table("timeline_events") as batch_op:
        batch_op.drop_column("status")
    for table_name in ("timeline_events", "character_knowledge", "character_states"):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("source_candidate_id")
    with op.batch_alter_table("scene_versions") as batch_op:
        batch_op.drop_column("superseded_by_version_id")
        batch_op.drop_column("superseded_at")
    with op.batch_alter_table("scenes") as batch_op:
        batch_op.drop_column("is_stale")
