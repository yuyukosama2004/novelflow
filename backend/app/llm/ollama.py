from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from app.llm.base import LLMClient, LLMRequest, LLMResponse, LLMStreamChunk


class OllamaClient(LLMClient):
    """Ollama adapter."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3",
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout_seconds),
            )
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        client = await self._get_client()
        prompt = ""
        for msg in request.messages:
            prefix = "user" if msg.role == "user" else "assistant"
            prompt += f"[{prefix}]: {msg.content}\n"
        payload = {
            "model": request.model or self.default_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }
        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        return LLMResponse(
            content=data.get("response", ""),
            model=data.get("model", request.model or self.default_model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            finish_reason="stop" if data.get("done") else "length",
        )

    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[LLMStreamChunk]:
        client = await self._get_client()
        prompt = ""
        for msg in request.messages:
            prefix = "user" if msg.role == "user" else "assistant"
            prompt += f"[{prefix}]: {msg.content}\n"
        payload = {
            "model": request.model or self.default_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }
        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                import json

                data = json.loads(line)
                done = data.get("done", False)
                yield LLMStreamChunk(
                    content_delta=data.get("response", ""),
                    finish_reason="stop" if done else None,
                )

    async def list_models(self) -> list[str]:
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return [m["name"] for m in data.get("models", [])]

    async def validate_connection(self) -> bool:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
