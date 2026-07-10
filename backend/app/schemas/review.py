from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ReviewRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scene_version_id: str
    model_profile_id: str | None
    status: str
    prompt_snapshot_json: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    summary: str
    created_at: datetime
    updated_at: datetime


class ReviewIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_run_id: str | None
    scene_version_id: str
    issue_type: str
    severity: str
    evidence_json: str
    conflict_rule: str
    suggestion: str
    confidence: float
    status: str
    created_at: datetime
    updated_at: datetime


class ReviewResultOut(BaseModel):
    run: ReviewRunOut
    issues: list[ReviewIssueOut]


class UpdateIssueStatusRequest(BaseModel):
    status: str
