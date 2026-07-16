from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CanonCommitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scene_id: str
    scene_version_id: str
    previous_commit_id: str | None
    sequence_no: int
    content_hash: str
    contract_snapshot_json: dict[str, Any]
    review_snapshot_json: dict[str, Any]
    commit_reason: str
    override_reason: str | None
    committed_by: str
    committed_at: datetime
