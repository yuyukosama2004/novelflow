from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ChangeSet(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "change_sets"
    __table_args__ = (
        CheckConstraint(
            "length(base_document_hash) = 64",
            name="ck_change_set_base_document_hash_length",
        ),
    )

    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    base_working_revision: Mapped[int] = mapped_column(Integer, default=0)
    base_document_hash: Mapped[str] = mapped_column(String(64))
    base_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("scene_versions.id"),
        nullable=True,
        index=True,
    )
    purpose: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="pending")
    workflow_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_runs.id"),
        nullable=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    applied_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("scene_versions.id"),
        nullable=True,
    )

    operations = relationship(
        "ChangeOperation",
        back_populates="change_set",
        cascade="all, delete-orphan",
        order_by="ChangeOperation.sequence_no",
    )


class ChangeOperation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "change_operations"
    __table_args__ = (
        UniqueConstraint(
            "change_set_id",
            "sequence_no",
            name="uq_change_operation_sequence",
        ),
    )

    change_set_id: Mapped[str] = mapped_column(
        ForeignKey("change_sets.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer)
    operation_type: Mapped[str] = mapped_column(String(40))
    target_node_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anchor_before_node_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    anchor_after_node_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    original_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    proposed_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    original_hash: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(40), default="pending")
    accepted_draft_revision: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conflict_reason: Mapped[str] = mapped_column(Text, default="")
    application_mode: Mapped[str] = mapped_column(String(40), default="")

    change_set = relationship("ChangeSet", back_populates="operations")
