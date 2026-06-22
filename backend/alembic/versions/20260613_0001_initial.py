"""initial schema

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260613_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "novel_projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("genre", sa.String(length=80), nullable=False),
        sa.Column("theme_json", sa.JSON(), nullable=False),
        sa.Column("target_word_count", sa.Integer(), nullable=True),
        sa.Column("pov_type", sa.String(length=80), nullable=False),
        sa.Column("tone", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("current_timeline_position", sa.Integer(), nullable=False),
        *timestamps(),
    )

    op.create_table(
        "characters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("novel_projects.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("aliases_json", sa.JSON(), nullable=False),
        sa.Column("role", sa.String(length=80), nullable=False),
        sa.Column("age_text", sa.String(length=80), nullable=False),
        sa.Column("appearance", sa.Text(), nullable=False),
        sa.Column("background", sa.Text(), nullable=False),
        sa.Column("public_identity", sa.Text(), nullable=False),
        sa.Column("secret_identity", sa.Text(), nullable=False),
        sa.Column("core_desire", sa.Text(), nullable=False),
        sa.Column("core_fear", sa.Text(), nullable=False),
        sa.Column("values_json", sa.JSON(), nullable=False),
        sa.Column("decision_pattern", sa.Text(), nullable=False),
        sa.Column("stress_response", sa.Text(), nullable=False),
        sa.Column("speech_style", sa.Text(), nullable=False),
        sa.Column("moral_boundaries_json", sa.JSON(), nullable=False),
        sa.Column("ability_limits_json", sa.JSON(), nullable=False),
        sa.Column("forbidden_behaviors_json", sa.JSON(), nullable=False),
        sa.Column("arc_plan", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_characters_project_id", "characters", ["project_id"])

    op.create_table(
        "world_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("novel_projects.id"),
            nullable=False,
        ),
        sa.Column("entry_type", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=False),
        sa.Column("canon_status", sa.String(length=40), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_world_entries_project_id", "world_entries", ["project_id"])

    op.create_table(
        "volumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("novel_projects.id"),
            nullable=False,
        ),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("project_id", "sequence_no", name="uq_volume_sequence"),
    )
    op.create_index("ix_volumes_project_id", "volumes", ["project_id"])

    op.create_table(
        "character_states",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "character_id",
            sa.String(length=36),
            sa.ForeignKey("characters.id"),
            nullable=False,
        ),
        sa.Column("timeline_order", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=True),
        sa.Column("physical_state_json", sa.JSON(), nullable=False),
        sa.Column("emotional_state", sa.Text(), nullable=False),
        sa.Column("current_goal", sa.Text(), nullable=False),
        sa.Column("current_pressure", sa.Text(), nullable=False),
        sa.Column("resources_json", sa.JSON(), nullable=False),
        sa.Column("injuries_json", sa.JSON(), nullable=False),
        sa.Column("active_secrets_json", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("source_scene_version_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_character_states_character_id", "character_states", ["character_id"])

    op.create_table(
        "character_knowledge",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "character_id",
            sa.String(length=36),
            sa.ForeignKey("characters.id"),
            nullable=False,
        ),
        sa.Column("fact_key", sa.String(length=200), nullable=False),
        sa.Column("fact_value_json", sa.JSON(), nullable=False),
        sa.Column("knowledge_status", sa.String(length=40), nullable=False),
        sa.Column("learned_at_scene_version_id", sa.String(length=36), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        *timestamps(),
    )
    op.create_index("ix_character_knowledge_character_id", "character_knowledge", ["character_id"])

    op.create_table(
        "chapters",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("volume_id", sa.String(length=36), sa.ForeignKey("volumes.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("approved_word_count", sa.Integer(), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("volume_id", "sequence_no", name="uq_chapter_sequence"),
    )
    op.create_index("ix_chapters_volume_id", "chapters", ["volume_id"])

    op.create_table(
        "scenes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("chapter_id", sa.String(length=36), sa.ForeignKey("chapters.id"), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("pov_character_id", sa.String(length=36), nullable=True),
        sa.Column("time_text", sa.String(length=160), nullable=False),
        sa.Column("timeline_order", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.String(length=36), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("conflict", sa.Text(), nullable=False),
        sa.Column("turning_point", sa.Text(), nullable=False),
        sa.Column("ending_hook", sa.Text(), nullable=False),
        sa.Column("must_include_json", sa.JSON(), nullable=False),
        sa.Column("must_not_reveal_json", sa.JSON(), nullable=False),
        sa.Column("forbidden_actions_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("approved_version_id", sa.String(length=36), nullable=True),
        *timestamps(),
        sa.UniqueConstraint("chapter_id", "sequence_no", name="uq_scene_sequence"),
    )
    op.create_index("ix_scenes_chapter_id", "scenes", ["chapter_id"])

    op.create_table(
        "scene_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("scene_id", sa.String(length=36), sa.ForeignKey("scenes.id"), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("parent_version_id", sa.String(length=36), nullable=True),
        sa.Column("branch_name", sa.String(length=100), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("model_profile_id", sa.String(length=36), nullable=True),
        sa.Column("prompt_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("context_manifest_json", sa.JSON(), nullable=False),
        sa.Column("review_status", sa.String(length=40), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        *timestamps(),
        sa.UniqueConstraint("scene_id", "version_no", name="uq_scene_version_no"),
    )
    op.create_index("ix_scene_versions_scene_id", "scene_versions", ["scene_id"])


def downgrade() -> None:
    op.drop_table("scene_versions")
    op.drop_table("scenes")
    op.drop_table("chapters")
    op.drop_table("character_knowledge")
    op.drop_table("character_states")
    op.drop_table("volumes")
    op.drop_table("world_entries")
    op.drop_table("characters")
    op.drop_table("novel_projects")
