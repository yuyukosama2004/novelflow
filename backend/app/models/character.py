from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Character(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "characters"

    project_id: Mapped[str] = mapped_column(ForeignKey("novel_projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    aliases_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    role: Mapped[str] = mapped_column(String(80), default="")
    age_text: Mapped[str] = mapped_column(String(80), default="")
    appearance: Mapped[str] = mapped_column(Text, default="")
    background: Mapped[str] = mapped_column(Text, default="")
    public_identity: Mapped[str] = mapped_column(Text, default="")
    secret_identity: Mapped[str] = mapped_column(Text, default="")
    core_desire: Mapped[str] = mapped_column(Text, default="")
    core_fear: Mapped[str] = mapped_column(Text, default="")
    values_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    decision_pattern: Mapped[str] = mapped_column(Text, default="")
    stress_response: Mapped[str] = mapped_column(Text, default="")
    speech_style: Mapped[str] = mapped_column(Text, default="")
    moral_boundaries_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    ability_limits_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    forbidden_behaviors_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    arc_plan: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="active")
    version: Mapped[int] = mapped_column(Integer, default=1)

    project = relationship("NovelProject", back_populates="characters")
    states = relationship(
        "CharacterState",
        back_populates="character",
        cascade="all, delete-orphan",
    )
    knowledge = relationship(
        "CharacterKnowledge",
        back_populates="character",
        cascade="all, delete-orphan",
    )


class CharacterState(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "character_states"

    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"), index=True)
    timeline_order: Mapped[int] = mapped_column(Integer, default=0)
    location_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    physical_state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    emotional_state: Mapped[str] = mapped_column(Text, default="")
    current_goal: Mapped[str] = mapped_column(Text, default="")
    current_pressure: Mapped[str] = mapped_column(Text, default="")
    resources_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    injuries_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active_secrets_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(Text, default="")
    source_scene_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source_candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="confirmed")

    character = relationship("Character", back_populates="states")


class CharacterKnowledge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "character_knowledge"

    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"), index=True)
    fact_key: Mapped[str] = mapped_column(String(200))
    fact_value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    knowledge_status: Mapped[str] = mapped_column(String(40), default="unknown")
    learned_at_scene_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    record_status: Mapped[str] = mapped_column(String(40), default="active")
    source_candidate_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    character = relationship("Character", back_populates="knowledge")
