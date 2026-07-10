from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReviewRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_runs"

    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id"), index=True)
    model_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    provider: Mapped[str] = mapped_column(String(40), default="")
    model: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(40), default="pending")
    prompt_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")

    scene_version = relationship("SceneVersion", back_populates="review_runs")
    issues = relationship(
        "ReviewIssue",
        back_populates="review_run",
        cascade="all, delete-orphan",
        foreign_keys="ReviewIssue.review_run_id",
    )


class ReviewIssue(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "review_issues"

    review_run_id: Mapped[str | None] = mapped_column(ForeignKey("review_runs.id"), index=True, nullable=True)
    scene_version_id: Mapped[str] = mapped_column(ForeignKey("scene_versions.id"), index=True)
    issue_type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    evidence_json: Mapped[str] = mapped_column(Text, default="")
    conflict_rule: Mapped[str] = mapped_column(Text, default="")
    suggestion: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(
        String(40), default="open"
    )  # open | accepted | ignored | false_positive

    review_run = relationship("ReviewRun", back_populates="issues")
    scene_version = relationship("SceneVersion", back_populates="review_issues")
