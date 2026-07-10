from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EntityBase

SceneStatus = Literal[
    "unplanned",
    "planned",
    "ready",
    "drafting",
    "reviewing",
    "approved",
    "canonicalizing",
    "needs_revision",
]
SceneSourceType = Literal["human", "ai_generated", "ai_revised", "human_revised", "merged"]


class VolumeCreate(BaseModel):
    sequence_no: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    goal: str = ""
    status: str = "draft"


class VolumeUpdate(BaseModel):
    sequence_no: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    goal: str | None = None
    status: str | None = None


class VolumeRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    sequence_no: int
    title: str
    summary: str
    goal: str
    status: str


class ChapterCreate(BaseModel):
    sequence_no: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    goal: str = ""
    status: str = "draft"
    approved_word_count: int = 0


class ChapterUpdate(BaseModel):
    sequence_no: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    goal: str | None = None
    status: str | None = None
    approved_word_count: int | None = Field(default=None, ge=0)


class ChapterRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    volume_id: str
    sequence_no: int
    title: str
    summary: str
    goal: str
    status: str
    approved_word_count: int


class SceneCreate(BaseModel):
    sequence_no: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    pov_character_id: str | None = None
    time_text: str = ""
    timeline_order: int = 0
    location_id: str | None = None
    goal: str = ""
    conflict: str = ""
    turning_point: str = ""
    ending_hook: str = ""
    must_include_json: list[str] = Field(default_factory=list)
    must_not_reveal_json: list[str] = Field(default_factory=list)
    forbidden_actions_json: list[str] = Field(default_factory=list)
    status: SceneStatus = "unplanned"


class SceneUpdate(BaseModel):
    sequence_no: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    pov_character_id: str | None = None
    time_text: str | None = None
    timeline_order: int | None = None
    location_id: str | None = None
    goal: str | None = None
    conflict: str | None = None
    turning_point: str | None = None
    ending_hook: str | None = None
    must_include_json: list[str] | None = None
    must_not_reveal_json: list[str] | None = None
    forbidden_actions_json: list[str] | None = None
    status: SceneStatus | None = None


class SceneRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    chapter_id: str
    sequence_no: int
    title: str
    pov_character_id: str | None
    time_text: str
    timeline_order: int
    location_id: str | None
    goal: str
    conflict: str
    turning_point: str
    ending_hook: str
    must_include_json: list[str]
    must_not_reveal_json: list[str]
    forbidden_actions_json: list[str]
    status: str
    approved_version_id: str | None


class SceneReorderItem(BaseModel):
    scene_id: str
    sequence_no: int = Field(ge=1)


class SceneReorderRequest(BaseModel):
    chapter_id: str
    items: list[SceneReorderItem] = Field(min_length=1)


class SceneVersionCreate(BaseModel):
    parent_version_id: str | None = None
    branch_name: str = "main"
    content_markdown: str = ""
    summary: str = ""
    source_type: SceneSourceType = "human"
    model_profile_id: str | None = None
    prompt_snapshot_json: dict[str, Any] = Field(default_factory=dict)
    context_manifest_json: dict[str, Any] = Field(default_factory=dict)
    review_status: str = "not_reviewed"
    created_by: str = "user"


class SceneVersionRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    scene_id: str
    version_no: int
    parent_version_id: str | None
    branch_name: str
    content_markdown: str
    summary: str
    source_type: str
    model_profile_id: str | None
    prompt_snapshot_json: dict[str, Any]
    context_manifest_json: dict[str, Any]
    review_status: str
    created_by: str
    approved_at: datetime | None
    approval_override_reason: str | None


class ApproveVersionRequest(BaseModel):
    version_id: str
    override_reason: str | None = None


class VersionCompareRead(BaseModel):
    left: SceneVersionRead
    right: SceneVersionRead
    changed: bool
