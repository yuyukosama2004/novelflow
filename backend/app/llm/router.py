from __future__ import annotations

from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.llm.base import LLMClient, LLMRequest, LLMResponse, LLMStreamChunk
from app.llm.deepseek import DeepSeekClient
from app.llm.fake import FakeLLMClient
from app.llm.ollama import OllamaClient
from app.llm.openai_compatible import OpenAICompatibleClient
from app.models.model_profile import ModelProfile


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

    def __init__(self, profile: ModelProfile | None = None) -> None:
        self.settings = get_settings()
        self.profile = profile

    @staticmethod
    def client_from_profile(profile: ModelProfile) -> LLMClient:
        if not profile.enabled:
            raise ModelConfigurationError(
                "model profile is disabled",
                {"profile_id": profile.id},
            )
        if profile.provider == "deepseek":
            if not profile.api_key:
                raise ModelConfigurationError(
                    "DeepSeek API key is not configured",
                    {"profile_id": profile.id, "provider": profile.provider},
                )
            return DeepSeekClient(
                api_key=profile.api_key,
                base_url=profile.base_url or "https://api.deepseek.com",
                default_model=profile.model_name or "deepseek-chat",
                timeout_seconds=profile.timeout_seconds,
            )
        if profile.provider == "openai_compatible":
            if not profile.base_url:
                raise ModelConfigurationError(
                    "OpenAI-compatible base URL is not configured",
                    {"profile_id": profile.id, "provider": profile.provider},
                )
            return OpenAICompatibleClient(
                api_key=profile.api_key,
                base_url=profile.base_url,
                default_model=profile.model_name or "gpt-4o",
                timeout_seconds=profile.timeout_seconds,
            )
        if profile.provider == "ollama":
            return OllamaClient(
                base_url=profile.base_url or "http://localhost:11434",
                default_model=profile.model_name or "llama3",
                timeout_seconds=profile.timeout_seconds,
            )
        if profile.provider == "fake":
            return FakeLLMClient(model_name=profile.model_name or "fake-model")
        raise ModelConfigurationError(
            "unknown model provider",
            {"profile_id": profile.id, "provider": profile.provider},
        )

    def _get_client(self, provider: str) -> LLMClient:
        if self.profile is not None:
            if provider and provider != self.profile.provider:
                raise ModelConfigurationError(
                    "requested provider does not match model profile",
                    {
                        "profile_id": self.profile.id,
                        "provider": provider,
                    },
                )
            return self.client_from_profile(self.profile)
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
            raise ModelConfigurationError(
                "openai provider requires its own API key; use deepseek or openai_compatible instead",
                {"provider": provider},
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
        provider = provider or (
            self.profile.provider if self.profile else self.settings.default_model_provider
        )
        client = self._get_client(provider)
        try:
            return await client.generate(request)
        except AppError:
            raise
        except Exception as exc:
            raise ModelResponseError(
                f"model generation failed: {type(exc).__name__}",
                {"provider": provider},
            ) from exc

    async def stream_generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> AsyncIterator[LLMStreamChunk]:
        provider = provider or (
            self.profile.provider if self.profile else self.settings.default_model_provider
        )
        client = self._get_client(provider)
        try:
            async for chunk in client.stream_generate(request):
                yield chunk
        except AppError:
            raise
        except Exception as exc:
            raise ModelResponseError(
                f"model streaming failed: {type(exc).__name__}",
                {"provider": provider},
            ) from exc

    async def validate_connection(self, provider: str = "") -> bool:
        if self.profile is not None:
            provider = provider or self.profile.provider
        else:
            provider = provider or self.settings.default_model_provider
        client = self._get_client(provider)
        return await client.validate_connection()
