from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator


class CharacterStateContent(BaseModel):
    physical_state: dict[str, Any] = Field(default_factory=dict)
    emotional_state: str = ""
    current_goal: str = ""
    current_pressure: str = ""
    resources: dict[str, Any] = Field(default_factory=dict)
    injuries: dict[str, Any] = Field(default_factory=dict)
    active_secrets: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def must_include_a_change(self) -> CharacterStateContent:
        if not self.model_fields_set:
            raise ValueError("character state must include at least one field")
        return self


class CharacterKnowledgeContent(BaseModel):
    fact_key: str = Field(min_length=1, max_length=200)
    fact_value_json: dict[str, Any] = Field(default_factory=dict)
    knowledge_status: Literal[
        "unknown",
        "suspected",
        "believed",
        "confirmed",
        "misunderstood",
        "forgotten",
    ] = "confirmed"


class TimelineEventContent(BaseModel):
    event_text: str = Field(min_length=1)
    affected_character_ids: list[str] = Field(default_factory=list)


class RelationshipChangeContent(BaseModel):
    character_a_id: str
    character_b_id: str
    relation_type: Literal[
        "ally",
        "rival",
        "lover",
        "family",
        "mentor",
        "conflict",
        "secret",
        "other",
    ] = "other"
    description: str = ""
    timeline_info: str = ""

    @model_validator(mode="after")
    def characters_must_differ(self) -> RelationshipChangeContent:
        if self.character_a_id == self.character_b_id:
            raise ValueError("relationship characters must differ")
        return self


class WorldFactUpdateContent(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=180)
    entry_type: (
        Literal[
            "rule",
            "location",
            "organization",
            "item",
            "ability",
            "history",
            "term",
            "custom",
        ]
        | None
    ) = None
    summary: str | None = None
    content: str | None = None
    tags_json: list[str] | None = None

    @model_validator(mode="after")
    def must_include_an_update(self) -> WorldFactUpdateContent:
        if not any(getattr(self, field_name) is not None for field_name in self.model_fields_set):
            raise ValueError("world fact update must include at least one field")
        return self


class MemoryItemBase(BaseModel):
    target_entity_type: str
    target_entity_id: str | None = None
    evidence: str = ""
    confidence: float = Field(ge=0.0, le=1.0)


class CharacterStateMemoryItem(MemoryItemBase):
    candidate_type: Literal["character_state"]
    target_entity_type: Literal["character"]
    target_entity_id: str
    content_json: CharacterStateContent


class CharacterKnowledgeMemoryItem(MemoryItemBase):
    candidate_type: Literal["character_knowledge"]
    target_entity_type: Literal["character"]
    target_entity_id: str
    content_json: CharacterKnowledgeContent


class TimelineEventMemoryItem(MemoryItemBase):
    candidate_type: Literal["timeline_event"]
    target_entity_type: Literal["scene", "timeline"]
    content_json: TimelineEventContent


class RelationshipChangeMemoryItem(MemoryItemBase):
    candidate_type: Literal["relationship_change"]
    target_entity_type: Literal["relationship"]
    content_json: RelationshipChangeContent


class WorldFactUpdateMemoryItem(MemoryItemBase):
    candidate_type: Literal["world_fact_update"]
    target_entity_type: Literal["world_entry"]
    target_entity_id: str
    content_json: WorldFactUpdateContent


MemoryItemValue = Annotated[
    CharacterStateMemoryItem
    | CharacterKnowledgeMemoryItem
    | TimelineEventMemoryItem
    | RelationshipChangeMemoryItem
    | WorldFactUpdateMemoryItem,
    Field(discriminator="candidate_type"),
]


class MemoryItem(RootModel[MemoryItemValue]):
    pass


class MemoryExtractionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_version_id: str
    model_profile_id: str | None
    provider: str
    model: str
    status: str
    prompt_snapshot_json: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MemoryCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    extraction_run_id: str | None
    scene_version_id: str
    candidate_type: str
    target_entity_type: str
    target_entity_id: str | None
    content_json: dict[str, Any]
    evidence: str
    confidence: float
    source_chunk_index: int
    source_start: int
    source_end: int
    status: str
    created_at: datetime
    updated_at: datetime


class MemoryExtractionResultOut(BaseModel):
    run: MemoryExtractionRunOut
    candidates: list[MemoryCandidateOut]


class UpdateCandidateRequest(BaseModel):
    status: Literal["approved", "rejected"]
    content_json: dict[str, Any] | None = None
