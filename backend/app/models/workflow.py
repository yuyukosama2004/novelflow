from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkflowRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        Index(
            "uq_workflow_active_scene",
            "scene_id",
            unique=True,
            sqlite_where=text("status IN ('pending', 'planning', 'drafting', 'queued', 'running')"),
        ),
        Index("uq_workflow_idempotency_key", "idempotency_key", unique=True),
    )

    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    model_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_type: Mapped[str] = mapped_column(String(40), default="scene_writing")
    status: Mapped[str] = mapped_column(String(40), default="queued")
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64), default="")
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    last_event_sequence: Mapped[int] = mapped_column(Integer, default=0)
    current_step_key: Mapped[str] = mapped_column(String(80), default="")
    last_healthy_step_key: Mapped[str] = mapped_column(String(80), default="")
    lease_owner: Mapped[str] = mapped_column(String(100), default="")
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(40), default="")
    model: Mapped[str] = mapped_column(String(80), default="")
    plan: Mapped[str] = mapped_column(Text, default="")
    draft: Mapped[str] = mapped_column(Text, default="")
    final_content: Mapped[str] = mapped_column(Text, default="")
    prompt_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    context_manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    events_json: Mapped[list[dict]] = mapped_column(JSON, default=list)
    error: Mapped[str] = mapped_column(Text, default="")
    version_created_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    scene = relationship("Scene", back_populates="workflow_runs")
    step_runs = relationship(
        "WorkflowStepRun",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowStepRun.created_at",
    )
    events = relationship(
        "WorkflowEvent",
        back_populates="workflow_run",
        cascade="all, delete-orphan",
        order_by="WorkflowEvent.sequence_no",
    )


class WorkflowStepRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_step_runs"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "step_key",
            "attempt",
            name="uq_workflow_step_attempt",
        ),
    )

    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    step_key: Mapped[str] = mapped_column(String(80))
    attempt: Mapped[int] = mapped_column(Integer)
    worker_id: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(40), default="running")
    input_hash: Mapped[str] = mapped_column(String(64))
    raw_output: Mapped[str] = mapped_column(Text, default="")
    raw_output_hash: Mapped[str] = mapped_column(String(64), default="")
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_hash: Mapped[str] = mapped_column(String(64), default="")
    checkpoint_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error_code: Mapped[str] = mapped_column(String(80), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    retryable: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow_run = relationship("WorkflowRun", back_populates="step_runs")


class WorkflowEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_events"
    __table_args__ = (
        UniqueConstraint(
            "workflow_run_id",
            "sequence_no",
            name="uq_workflow_event_sequence",
        ),
    )

    workflow_run_id: Mapped[str] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(80))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    workflow_run = relationship("WorkflowRun", back_populates="events")
