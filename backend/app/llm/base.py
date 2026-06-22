from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMRequest:
    messages: list[LLMMessage]
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    stop: list[str] | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"
    usage_extra: dict = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    content_delta: str
    finish_reason: str | None = None


class LLMClient(ABC):
    """Unified abstract interface for every model adapter."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(content_delta="")  # pragma: no cover

    @abstractmethod
    async def validate_connection(self) -> bool: ...
