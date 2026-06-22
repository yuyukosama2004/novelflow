from __future__ import annotations

from collections.abc import AsyncIterator

from app.llm.base import LLMClient, LLMRequest, LLMResponse, LLMStreamChunk


class FakeLLMClient(LLMClient):
    """Deterministic fake client for tests and development."""

    def __init__(
        self,
        fixed_response: str | None = None,
        fixed_json: str | None = None,
        stream_chunks: list[str] | None = None,
        simulate_timeout: bool = False,
        simulate_rate_limit: bool = False,
        simulate_format_error: bool = False,
        model_name: str = "fake-model",
    ) -> None:
        self.fixed_response = fixed_response or ""
        self.fixed_json = fixed_json
        self.stream_chunks = stream_chunks
        self.simulate_timeout = simulate_timeout
        self.simulate_rate_limit = simulate_rate_limit
        self.simulate_format_error = simulate_format_error
        self.model_name = model_name

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if self.simulate_timeout:
            import asyncio

            raise asyncio.TimeoutError("fake timeout")
        if self.simulate_rate_limit:
            raise FakeRateLimitError("fake rate limit")
        if self.simulate_format_error:
            return LLMResponse(
                content='{"broken": ',
                model=self.model_name,
                finish_reason="stop",
            )
        if self.fixed_json:
            return LLMResponse(
                content=self.fixed_json,
                model=self.model_name,
                prompt_tokens=10,
                completion_tokens=len(self.fixed_json) // 4,
                finish_reason="stop",
            )
        content = self.fixed_response
        if not content:
            content = "林默靠在医院走廊的墙上，左臂隐隐作痛。他看着苏岚走近，神色平静如水，却什么都没说。"
        return LLMResponse(
            content=content,
            model=self.model_name,
            prompt_tokens=10,
            completion_tokens=max(len(content) // 4, 1),
            finish_reason="stop",
        )

    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        if self.simulate_timeout:
            import asyncio

            raise asyncio.TimeoutError("fake timeout")
        if self.simulate_rate_limit:
            raise FakeRateLimitError("fake rate limit")
        content = self.fixed_response or ("林默靠在医院走廊的墙上，左臂隐隐作痛。")
        if self.stream_chunks:
            chunks = self.stream_chunks
        else:
            chunks = [content[i : i + 5] for i in range(0, len(content), 5)]
        for i, chunk in enumerate(chunks):
            yield LLMStreamChunk(
                content_delta=chunk,
                finish_reason="stop" if i == len(chunks) - 1 else None,
            )

    async def validate_connection(self) -> bool:
        return True


class FakeRateLimitError(Exception):
    pass
