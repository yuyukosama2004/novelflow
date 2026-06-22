from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class MemoryCandidate(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "memory_candidates"

    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id"), index=True)
    candidate_type: Mapped[str] = mapped_column(String(40))
    target_entity_type: Mapped[str] = mapped_column(String(40))
    target_entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    status: Mapped[str] = mapped_column(
        String(40), default="pending"
    )  # pending | approved | rejected | conflicted

    scene_version = relationship("SceneVersion", back_populates="memory_candidates")


class TimelineEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "timeline_events"

    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id"), index=True)
    scene_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_text: Mapped[str] = mapped_column(Text, default="")
    timeline_order: Mapped[int] = mapped_column(Integer, default=0)
    affected_character_ids: Mapped[list[str]] = mapped_column(JSON, default=list)

    project = relationship("NovelProject", back_populates="timeline_events")
