from __future__ import annotations

from app.llm.openai_compatible import OpenAICompatibleClient


class DeepSeekClient(OpenAICompatibleClient):
    """DeepSeek API adapter."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-v4-flash",
        timeout_seconds: float = 120.0,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            default_model=default_model,
            timeout_seconds=timeout_seconds,
        )
