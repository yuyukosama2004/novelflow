from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EntityBase

ProjectStatus = Literal["draft", "active", "archived", "completed"]
NarrativePerspective = Literal[
    "first_person",
    "third_person_limited",
    "third_person_omniscient",
]
WritingStylePreset = Literal[
    "general_web",
    "light_novel",
    "male_web",
    "female_web",
    "suspense",
    "literary",
    "historical",
    "scifi",
    "custom",
]


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    genre: str = ""
    theme_json: dict[str, Any] = Field(default_factory=dict)
    target_word_count: int | None = Field(default=None, ge=0)
    pov_type: NarrativePerspective = "third_person_limited"
    tone: str = ""
    writing_style_preset: WritingStylePreset = "general_web"
    writing_style_custom: str = Field(default="", max_length=2000)
    default_scene_word_count: int = Field(default=1000, ge=300, le=10000)
    status: ProjectStatus = "draft"
    language: str = "zh-CN"
    current_timeline_position: int = 0
    default_model_profile_id: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    genre: str | None = None
    theme_json: dict[str, Any] | None = None
    target_word_count: int | None = Field(default=None, ge=0)
    pov_type: NarrativePerspective | None = None
    tone: str | None = None
    writing_style_preset: WritingStylePreset | None = None
    writing_style_custom: str | None = Field(default=None, max_length=2000)
    default_scene_word_count: int | None = Field(default=None, ge=300, le=10000)
    status: ProjectStatus | None = None
    language: str | None = None
    current_timeline_position: int | None = None
    default_model_profile_id: str | None = None


class ProjectRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    title: str
    summary: str
    genre: str
    theme_json: dict[str, Any]
    target_word_count: int | None
    pov_type: str
    tone: str
    writing_style_preset: str
    writing_style_custom: str
    default_scene_word_count: int
    status: str
    language: str
    current_timeline_position: int
    default_model_profile_id: str | None
