"""模型配置服务：管理用户配置的 AI provider 和模型选择。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.llm.router import LLMRouter
from app.models.model_profile import ModelProfile

# DeepSeek 已知模型列表
DEEPSEEK_MODELS = ["deepseek-chat", "deepseek-reasoner"]


class ModelProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payload: dict) -> ModelProfile:
        if payload.get("is_default"):
            await self._clear_defaults()
        profile = ModelProfile(**payload)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def list_all(self) -> list[ModelProfile]:
        result = await self.session.execute(
            select(ModelProfile).order_by(ModelProfile.is_default.desc(), ModelProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, profile_id: str) -> ModelProfile:
        p = await self.session.get(ModelProfile, profile_id)
        if p is None:
            raise NotFoundError("model profile not found", {"profile_id": profile_id})
        return p

    async def update(self, profile_id: str, payload: dict) -> ModelProfile:
        p = await self.get(profile_id)
        if payload.get("is_default"):
            await self._clear_defaults()
        for key, value in payload.items():
            if hasattr(p, key):
                setattr(p, key, value)
        await self.session.commit()
        await self.session.refresh(p)
        return p

    async def delete(self, profile_id: str) -> None:
        p = await self.get(profile_id)
        if p.is_default:
            raise ConflictError("cannot delete default profile")
        await self.session.delete(p)
        await self.session.commit()

    async def test(self, profile_id: str) -> dict:
        p = await self.get(profile_id)
        router = LLMRouter()
        try:
            connected = await router.validate_connection(p.provider)
            if connected:
                return {"connected": True, "provider": p.provider, "model": p.model_name}
            return {"connected": False, "error": "connection test failed"}
        except Exception as exc:
            return {"connected": False, "error": str(exc)}

    async def get_default(self) -> ModelProfile | None:
        result = await self.session.execute(
            select(ModelProfile).where(ModelProfile.is_default.is_(True), ModelProfile.enabled.is_(True))
        )
        return result.scalar_one_or_none()

    @staticmethod
    def get_provider_models(provider: str) -> list[str]:
        if provider == "deepseek":
            return list(DEEPSEEK_MODELS)
        if provider == "ollama":
            return []  # 前端通过 API 动态获取
        return []  # openai_compatible 由用户手动输入

    async def _clear_defaults(self) -> None:
        result = await self.session.execute(
            select(ModelProfile).where(ModelProfile.is_default.is_(True))
        )
        for p in result.scalars().all():
            p.is_default = False

    @staticmethod
    def _out(p: ModelProfile) -> dict:
        return {
            "id": p.id,
            "name": p.name,
            "provider": p.provider,
            "base_url": p.base_url,
            "api_key_configured": bool(p.api_key),
            "model_name": p.model_name,
            "temperature": p.temperature,
            "max_output_tokens": p.max_output_tokens,
            "timeout_seconds": p.timeout_seconds,
            "is_default": p.is_default,
            "enabled": p.enabled,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
