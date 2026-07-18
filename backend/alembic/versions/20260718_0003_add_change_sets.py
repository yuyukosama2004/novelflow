"""add change sets

Revision ID: 20260718_0003
Revises: 20260718_0002
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0003"
down_revision: str | None = "20260718_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "change_sets",
        sa.Column("scene_id", sa.String(length=36), nullable=False),
        sa.Column("base_working_revision", sa.Integer(), nullable=False),
        sa.Column("base_document_hash", sa.String(length=64), nullable=False),
        sa.Column("base_version_id", sa.String(length=36), nullable=True),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("workflow_run_id", sa.String(length=36), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("applied_version_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(base_document_hash) = 64",
            name="ck_change_set_base_document_hash_length",
        ),
        sa.ForeignKeyConstraint(["applied_version_id"], ["scene_versions.id"]),
        sa.ForeignKeyConstraint(["base_version_id"], ["scene_versions.id"]),
        sa.ForeignKeyConstraint(["scene_id"], ["scenes.id"]),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("scene_id", "base_version_id", "workflow_run_id"):
        op.create_index(
            op.f(f"ix_change_sets_{column}"),
            "change_sets",
            [column],
            unique=False,
        )

    op.create_table(
        "change_operations",
        sa.Column("change_set_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(length=40), nullable=False),
        sa.Column("target_node_id", sa.String(length=36), nullable=True),
        sa.Column("anchor_before_node_id", sa.String(length=36), nullable=True),
        sa.Column("anchor_after_node_id", sa.String(length=36), nullable=True),
        sa.Column("original_json", sa.JSON(), nullable=False),
        sa.Column("proposed_json", sa.JSON(), nullable=False),
        sa.Column("original_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("accepted_draft_revision", sa.Integer(), nullable=True),
        sa.Column("conflict_reason", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["change_set_id"],
            ["change_sets.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "change_set_id",
            "sequence_no",
            name="uq_change_operation_sequence",
        ),
    )
    op.create_index(
        op.f("ix_change_operations_change_set_id"),
        "change_operations",
        ["change_set_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_change_operations_change_set_id"),
        table_name="change_operations",
    )
    op.drop_table("change_operations")
    for column in ("workflow_run_id", "base_version_id", "scene_id"):
        op.drop_index(op.f(f"ix_change_sets_{column}"), table_name="change_sets")
    op.drop_table("change_sets")
