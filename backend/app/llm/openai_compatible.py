from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from app.llm.base import LLMClient, LLMRequest, LLMResponse, LLMStreamChunk


class OpenAICompatibleClient(LLMClient):
    """Adapter for any OpenAI-compatible API (DeepSeek, vLLM, etc.)."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-4o",
        timeout_seconds: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.timeout_seconds),
            )
        return self._client

    def _build_payload(self, request: LLMRequest) -> dict:
        return {
            "model": request.model or self.default_model,
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            **({"stop": request.stop} if request.stop else {}),
            **request.extra,
        }

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = await self._get_client()
        payload = self._build_payload(request)
        response = await client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", request.model or self.default_model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
            usage_extra=usage,
        )

    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        client = await self._get_client()
        payload = {**self._build_payload(request), "stream": True}
        async with client.stream("POST", "/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                import json

                data = json.loads(data_str)
                delta = data["choices"][0].get("delta", {})
                content_delta = delta.get("content", "")
                finish = data["choices"][0].get("finish_reason")
                yield LLMStreamChunk(
                    content_delta=content_delta,
                    finish_reason=finish,
                )

    async def validate_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False
