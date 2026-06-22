from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.llm.base import LLMClient, LLMRequest, LLMResponse, LLMStreamChunk
from app.llm.deepseek import DeepSeekClient
from app.llm.fake import FakeLLMClient
from app.llm.ollama import OllamaClient
from app.llm.openai_compatible import OpenAICompatibleClient


class ModelConnectionError(AppError):
    code = 50030
    status_code = 502


class ModelConfigurationError(AppError):
    code = 40030
    status_code = 400


class ModelResponseError(AppError):
    code = 50031
    status_code = 502


class LLMRouter:
    """Select and configure the right LLM client based on provider name."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _get_client(self, provider: str) -> LLMClient:
        if provider == "deepseek":
            if not self.settings.deepseek_api_key:
                raise ModelConfigurationError(
                    "DeepSeek API key is not configured",
                    {"provider": provider},
                )
            return DeepSeekClient(
                api_key=self.settings.deepseek_api_key,
                base_url=self.settings.deepseek_base_url,
            )
        if provider == "openai":
            return OpenAICompatibleClient(
                api_key=self.settings.deepseek_api_key,
            )
        if provider == "ollama":
            return OllamaClient(
                base_url=self.settings.ollama_base_url,
            )
        if provider == "fake":
            return FakeLLMClient()
        raise ModelConfigurationError(
            f"unknown model provider: {provider}",
            {"provider": provider},
        )

    async def generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> LLMResponse:
        provider = provider or self.settings.default_model_provider
        client = self._get_client(provider)
        try:
            return await client.generate(request)
        except AppError:
            raise
        except Exception as exc:
            raise ModelResponseError(
                f"model generation failed: {exc}",
                {"provider": provider, "error": str(exc)},
            ) from exc

    async def stream_generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> AsyncIterator[LLMStreamChunk]:
        provider = provider or self.settings.default_model_provider
        client = self._get_client(provider)
        try:
            async for chunk in client.stream_generate(request):
                yield chunk
        except AppError:
            raise
        except Exception as exc:
            raise ModelResponseError(
                f"model streaming failed: {exc}",
                {"provider": provider, "error": str(exc)},
            ) from exc

    async def validate_connection(self, provider: str) -> bool:
        client = self._get_client(provider)
        return await client.validate_connection()
