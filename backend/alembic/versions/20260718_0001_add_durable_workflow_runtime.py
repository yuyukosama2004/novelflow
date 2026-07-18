"""add durable workflow runtime

Revision ID: 20260718_0001
Revises: 20260716_0002
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260718_0001"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("uq_workflow_active_scene", table_name="workflow_runs")
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("input_hash", sa.String(length=64), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(
            sa.Column("current_step_key", sa.String(length=80), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column(
                "last_healthy_step_key",
                sa.String(length=80),
                nullable=False,
                server_default="",
            )
        )
        batch_op.add_column(
            sa.Column("lease_owner", sa.String(length=100), nullable=False, server_default="")
        )
        batch_op.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("blocked_reason", sa.Text(), nullable=False, server_default=""))

    op.create_index(
        "uq_workflow_active_scene",
        "workflow_runs",
        ["scene_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'planning', 'drafting', 'queued', 'running')"),
    )
    op.create_index(
        "uq_workflow_idempotency_key",
        "workflow_runs",
        ["idempotency_key"],
        unique=True,
    )
    op.create_table(
        "workflow_step_runs",
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("step_key", sa.String(length=80), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("worker_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_output", sa.Text(), nullable=False),
        sa.Column("raw_output_hash", sa.String(length=64), nullable=False),
        sa.Column("output_json", sa.JSON(), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_json", sa.JSON(), nullable=False),
        sa.Column("error_code", sa.String(length=80), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "step_key",
            "attempt",
            name="uq_workflow_step_attempt",
        ),
    )
    op.create_index(
        op.f("ix_workflow_step_runs_workflow_run_id"),
        "workflow_step_runs",
        ["workflow_run_id"],
        unique=False,
    )
    op.create_table(
        "workflow_events",
        sa.Column("workflow_run_id", sa.String(length=36), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_run_id",
            "sequence_no",
            name="uq_workflow_event_sequence",
        ),
    )
    op.create_index(
        op.f("ix_workflow_events_workflow_run_id"),
        "workflow_events",
        ["workflow_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_events_workflow_run_id"), table_name="workflow_events")
    op.drop_table("workflow_events")
    op.drop_index(
        op.f("ix_workflow_step_runs_workflow_run_id"),
        table_name="workflow_step_runs",
    )
    op.drop_table("workflow_step_runs")
    op.drop_index("uq_workflow_idempotency_key", table_name="workflow_runs")
    op.drop_index("uq_workflow_active_scene", table_name="workflow_runs")
    with op.batch_alter_table("workflow_runs") as batch_op:
        batch_op.drop_column("blocked_reason")
        batch_op.drop_column("cancel_requested_at")
        batch_op.drop_column("heartbeat_at")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_owner")
        batch_op.drop_column("last_healthy_step_key")
        batch_op.drop_column("current_step_key")
        batch_op.drop_column("attempt")
        batch_op.drop_column("input_hash")
        batch_op.drop_column("idempotency_key")
    op.create_index(
        "uq_workflow_active_scene",
        "workflow_runs",
        ["scene_id"],
        unique=True,
        sqlite_where=sa.text("status IN ('pending', 'planning', 'drafting')"),
    )
