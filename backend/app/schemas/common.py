from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T
    request_id: str


class ErrorResponse(BaseModel):
    code: int
    message: str
    details: dict[str, Any] | list[Any] = Field(default_factory=dict)
    request_id: str


class EntityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime
