from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Volume(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "volumes"
    __table_args__ = (UniqueConstraint("project_id", "sequence_no", name="uq_volume_sequence"),)

    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="draft")

    project = relationship("NovelProject", back_populates="volumes")
    chapters = relationship("Chapter", back_populates="volume", cascade="all, delete-orphan")


class Chapter(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("volume_id", "sequence_no", name="uq_chapter_sequence"),)

    volume_id: Mapped[str] = mapped_column(ForeignKey("volumes.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    goal: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="draft")
    approved_word_count: Mapped[int] = mapped_column(Integer, default=0)

    volume = relationship("Volume", back_populates="chapters")
    scenes = relationship("Scene", back_populates="chapter", cascade="all, delete-orphan")


class Scene(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scenes"
    __table_args__ = (UniqueConstraint("chapter_id", "sequence_no", name="uq_scene_sequence"),)

    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    pov_character_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    time_text: Mapped[str] = mapped_column(String(160), default="")
    story_time_order: Mapped[int] = mapped_column(Integer, default=1)
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    goal: Mapped[str] = mapped_column(Text, default="")
    conflict: Mapped[str] = mapped_column(Text, default="")
    turning_point: Mapped[str] = mapped_column(Text, default="")
    ending_hook: Mapped[str] = mapped_column(Text, default="")
    must_include_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    must_not_reveal_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    forbidden_actions_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(40), default="unplanned")
    approved_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    chapter = relationship("Chapter", back_populates="scenes")
    workflow_runs = relationship(
        "WorkflowRun",
        back_populates="scene",
        cascade="all, delete-orphan",
        foreign_keys="WorkflowRun.scene_id",
        order_by="WorkflowRun.created_at",
    )
    versions = relationship(
        "SceneVersion",
        back_populates="scene",
        cascade="all, delete-orphan",
        foreign_keys="SceneVersion.scene_id",
        order_by="SceneVersion.version_no",
    )
    working_draft = relationship(
        "SceneWorkingDraft",
        back_populates="scene",
        cascade="all, delete-orphan",
        uselist=False,
    )


class SceneWorkingDraft(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scene_working_drafts"

    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), unique=True, index=True)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    revision: Mapped[int] = mapped_column(Integer, default=1)

    scene = relationship("Scene", back_populates="working_draft")


class SceneVersion(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "scene_versions"
    __table_args__ = (UniqueConstraint("scene_id", "version_no", name="uq_scene_version_no"),)

    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    parent_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    branch_name: Mapped[str] = mapped_column(String(100), default="main")
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    content_markdown: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    source_type: Mapped[str] = mapped_column(String(40), default="human")
    model_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prompt_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    context_manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    review_status: Mapped[str] = mapped_column(String(40), default="not_reviewed")
    created_by: Mapped[str] = mapped_column(String(80), default="user")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    scene = relationship("Scene", back_populates="versions", foreign_keys=[scene_id])
    review_runs = relationship(
        "ReviewRun",
        back_populates="scene_version",
        cascade="all, delete-orphan",
        foreign_keys="ReviewRun.scene_version_id",
        order_by="ReviewRun.created_at",
    )
    review_issues = relationship(
        "ReviewIssue",
        back_populates="scene_version",
        cascade="all, delete-orphan",
        foreign_keys="ReviewIssue.scene_version_id",
    )
    memory_candidates = relationship(
        "MemoryCandidate",
        back_populates="scene_version",
        cascade="all, delete-orphan",
        foreign_keys="MemoryCandidate.scene_version_id",
    )
    memory_extraction_runs = relationship(
        "MemoryExtractionRun",
        back_populates="scene_version",
        cascade="all, delete-orphan",
        foreign_keys="MemoryExtractionRun.scene_version_id",
        order_by="MemoryExtractionRun.created_at",
    )
