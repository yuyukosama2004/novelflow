from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class MemoryExtractionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_version_id: str
    model_profile_id: str | None
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
    status: str
    created_at: datetime
    updated_at: datetime


class MemoryExtractionResultOut(BaseModel):
    run: MemoryExtractionRunOut
    candidates: list[MemoryCandidateOut]


class UpdateCandidateRequest(BaseModel):
    status: Literal["approved", "rejected"]
    content_json: dict[str, Any] | None = None
