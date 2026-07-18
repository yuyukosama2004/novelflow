from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import EntityBase
from app.schemas.manuscript import SceneWorkingDraftRead


class ChangeOperationCreate(BaseModel):
    sequence_no: int = Field(ge=1)
    operation_type: Literal[
        "insert_before",
        "insert_after",
        "replace_block",
        "delete_block",
    ]
    target_node_id: str | None = None
    anchor_before_node_id: str | None = None
    anchor_after_node_id: str | None = None
    original_json: dict[str, Any] = Field(default_factory=dict)
    proposed_json: dict[str, Any] = Field(default_factory=dict)
    original_hash: str = Field(default="", max_length=64)


class ChangeSetCreate(BaseModel):
    base_working_revision: int = Field(ge=0)
    base_version_id: str | None = None
    expected_base_document_hash: str | None = Field(default=None, min_length=64, max_length=64)
    purpose: Literal["generation", "rewrite", "review_fix", "restore", "merge"]
    workflow_run_id: str | None = None
    summary: str = Field(default="", max_length=2000)
    operations: list[ChangeOperationCreate] = Field(min_length=1)


class ChangeOperationRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    change_set_id: str
    sequence_no: int
    operation_type: str
    target_node_id: str | None
    anchor_before_node_id: str | None
    anchor_after_node_id: str | None
    original_json: dict[str, Any]
    proposed_json: dict[str, Any]
    original_hash: str
    status: str
    accepted_draft_revision: int | None
    conflict_reason: str


class ChangeSetRead(EntityBase):
    model_config = ConfigDict(from_attributes=True)

    scene_id: str
    base_working_revision: int
    base_document_hash: str
    base_version_id: str | None
    purpose: str
    status: str
    workflow_run_id: str | None
    summary: str
    applied_version_id: str | None
    operations: list[ChangeOperationRead]


class ChangeSetApplyRequest(BaseModel):
    expected_draft_revision: int = Field(ge=0)
    accept_operation_ids: set[str] = Field(default_factory=set)
    reject_operation_ids: set[str] = Field(default_factory=set)

    @model_validator(mode="after")
    def validate_decisions(self) -> ChangeSetApplyRequest:
        if self.accept_operation_ids & self.reject_operation_ids:
            raise ValueError("an operation cannot be both accepted and rejected")
        if not self.accept_operation_ids and not self.reject_operation_ids:
            raise ValueError("at least one operation decision is required")
        return self


class ChangeSetApplyRead(BaseModel):
    change_set: ChangeSetRead
    draft: SceneWorkingDraftRead | None
