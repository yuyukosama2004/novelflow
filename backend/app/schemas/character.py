from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EntityBase

KnowledgeStatus = Literal[
    "unknown",
    "suspected",
    "believed",
    "confirmed",
    "misunderstood",
    "forgotten",
]


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    aliases_json: list[str] = Field(default_factory=list)
    role: str = ""
    age_text: str = ""
    appearance: str = ""
    background: str = ""
    public_identity: str = ""
    secret_identity: str = ""
    core_desire: str = ""
    core_fear: str = ""
    values_json: list[str] = Field(default_factory=list)
    decision_pattern: str = ""
    stress_response: str = ""
    speech_style: str = ""
    moral_boundaries_json: list[str] = Field(default_factory=list)
    ability_limits_json: dict[str, Any] = Field(default_factory=dict)
    forbidden_behaviors_json: list[str] = Field(default_factory=list)
    arc_plan: str = ""
    status: str = "active"


class CharacterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    aliases_json: list[str] | None = None
    role: str | None = None
    age_text: str | None = None
    appearance: str | None = None
    background: str | None = None
    public_identity: str | None = None
    secret_identity: str | None = None
    core_desire: str | None = None
    core_fear: str | None = None
    values_json: list[str] | None = None
    decision_pattern: str | None = None
    stress_response: str | None = None
    speech_style: str | None = None
    moral_boundaries_json: list[str] | None = None
    ability_limits_json: dict[str, Any] | None = None
    forbidden_behaviors_json: list[str] | None = None
    arc_plan: str | None = None
    status: str | None = None


class CharacterRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    name: str
    aliases_json: list[str]
    role: str
    age_text: str
    appearance: str
    background: str
    public_identity: str
    secret_identity: str
    core_desire: str
    core_fear: str
    values_json: list[str]
    decision_pattern: str
    stress_response: str
    speech_style: str
    moral_boundaries_json: list[str]
    ability_limits_json: dict[str, Any]
    forbidden_behaviors_json: list[str]
    arc_plan: str
    status: str
    version: int


class CharacterStateCreate(BaseModel):
    timeline_order: int = 0
    location_id: str | None = None
    physical_state_json: dict[str, Any] = Field(default_factory=dict)
    emotional_state: str = ""
    current_goal: str = ""
    current_pressure: str = ""
    resources_json: dict[str, Any] = Field(default_factory=dict)
    injuries_json: dict[str, Any] = Field(default_factory=dict)
    active_secrets_json: list[str] = Field(default_factory=list)
    notes: str = ""
    source_scene_version_id: str | None = None
    status: str = "confirmed"


class CharacterStateRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    character_id: str
    timeline_order: int
    location_id: str | None
    physical_state_json: dict[str, Any]
    emotional_state: str
    current_goal: str
    current_pressure: str
    resources_json: dict[str, Any]
    injuries_json: dict[str, Any]
    active_secrets_json: list[str]
    notes: str
    source_scene_version_id: str | None
    status: str


class CharacterKnowledgeCreate(BaseModel):
    fact_key: str = Field(min_length=1, max_length=200)
    fact_value_json: dict[str, Any] = Field(default_factory=dict)
    knowledge_status: KnowledgeStatus = "unknown"
    learned_at_scene_version_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CharacterKnowledgeRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    character_id: str
    fact_key: str
    fact_value_json: dict[str, Any]
    knowledge_status: str
    learned_at_scene_version_id: str | None
    confidence: float
    record_status: str
