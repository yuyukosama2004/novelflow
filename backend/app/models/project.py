from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class NovelProject(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "novel_projects"

    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    genre: Mapped[str] = mapped_column(String(80), default="")
    theme_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    target_word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pov_type: Mapped[str] = mapped_column(String(80), default="")
    tone: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    language: Mapped[str] = mapped_column(String(40), default="zh-CN")
    current_timeline_position: Mapped[int] = mapped_column(Integer, default=0)
    default_model_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("model_profiles.id"), nullable=True
    )

    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    world_entries = relationship("WorldEntry", back_populates="project", cascade="all, delete-orphan")
    volumes = relationship("Volume", back_populates="project", cascade="all, delete-orphan")
    timeline_events = relationship(
        "TimelineEvent",
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="TimelineEvent.project_id",
    )
