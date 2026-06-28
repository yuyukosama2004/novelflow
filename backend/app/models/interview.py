"""访谈会话和故事候选模型。

访谈会话记录作者与 LLM 的创作讨论过程。
故事候选是 LLM 产出的设定建议，必须经作者确认后才写入正式实体。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class InterviewSession(UUIDMixin, TimestampMixin, Base):
    """一次创作访谈会话。"""

    __tablename__ = "interview_sessions"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id"), index=True
    )
    entry_type: Mapped[str] = mapped_column(
        String(40), default="idea"
    )  # idea | world | character | outline | direct
    title: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(
        String(40), default="active"
    )  # active | completed
    messages_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list
    )  # [{role, content, timestamp}]

    candidates = relationship(
        "StoryCandidate",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class StoryCandidate(UUIDMixin, TimestampMixin, Base):
    """LLM 产出的创作候选（人物/世界观/项目设定等），需作者确认。"""

    __tablename__ = "story_candidates"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("novel_projects.id"), index=True
    )
    session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id"), index=True
    )
    candidate_type: Mapped[str] = mapped_column(
        String(40), default="project_setting"
    )  # project_setting | character | world_entry
    title: Mapped[str] = mapped_column(String(200), default="")
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    proposal: Mapped[str] = mapped_column(Text, default="")  # LLM 建议理由
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    status: Mapped[str] = mapped_column(
        String(40), default="pending"
    )  # pending | approved | rejected
    applied_entity_type: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )  # project | character | world_entry
    applied_entity_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )  # 应用后关联的实际实体 ID

    session = relationship("InterviewSession", back_populates="candidates")
