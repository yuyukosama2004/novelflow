from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NovelFlow"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_version: str = "0.1.0"

    database_url: str = "sqlite+aiosqlite:///./novelflow.db"
    cors_origins: str = "http://localhost:5173"

    default_model_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    ollama_base_url: str = "http://localhost:11434"

    log_level: str = "INFO"
    workflow_max_revisions: int = 2
    workflow_max_json_repairs: int = 2
    sse_heartbeat_seconds: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def model_configuration_status(self) -> dict[str, bool]:
        return {
            "deepseek": bool(self.deepseek_api_key),
            "ollama": bool(self.ollama_base_url),
            "openai_compatible": bool(self.deepseek_api_key),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
