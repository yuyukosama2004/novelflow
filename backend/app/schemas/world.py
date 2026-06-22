from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import EntityBase

WorldEntryType = Literal[
    "rule",
    "location",
    "organization",
    "item",
    "ability",
    "history",
    "term",
    "custom",
]
CanonStatus = Literal["draft", "candidate", "approved", "deprecated", "conflicted"]


class WorldEntryCreate(BaseModel):
    entry_type: WorldEntryType = "custom"
    name: str = Field(min_length=1, max_length=180)
    summary: str = ""
    content: str = ""
    tags_json: list[str] = Field(default_factory=list)
    canon_status: CanonStatus = "draft"


class WorldEntryUpdate(BaseModel):
    entry_type: WorldEntryType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    summary: str | None = None
    content: str | None = None
    tags_json: list[str] | None = None
    canon_status: CanonStatus | None = None


class WorldEntryRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    entry_type: str
    name: str
    summary: str
    content: str
    tags_json: list[str]
    canon_status: str
    version: int
