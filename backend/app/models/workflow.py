from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class WorkflowRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "workflow_runs"

    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    model_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_type: Mapped[str] = mapped_column(String(40), default="scene_writing")
    status: Mapped[str] = mapped_column(String(40), default="pending")
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
