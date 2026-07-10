from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.llm.router import LLMRouter, ModelConfigurationError
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.model_profile import ModelProfile
from app.models.project import NovelProject


@dataclass(frozen=True)
class ModelRuntime:
    router: LLMRouter
    profile_id: str | None
    provider: str
    model: str


class ModelRuntimeResolver:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def resolve(
        self,
        project_id: str,
        requested_profile_id: str | None,
    ) -> ModelRuntime:
        profile_id = requested_profile_id
        if profile_id is None:
            project = await self.session.get(NovelProject, project_id)
            if project is None:
                raise ModelConfigurationError(
                    "project not found while resolving model profile",
                    {"project_id": project_id},
                )
            profile_id = project.default_model_profile_id

        profile = await self._profile(profile_id) if profile_id else None
        if profile is None:
            result = await self.session.execute(
                select(ModelProfile)
                .where(
                    ModelProfile.is_default.is_(True),
                    ModelProfile.enabled.is_(True),
                )
                .order_by(ModelProfile.created_at.desc())
                .limit(1)
            )
            profile = result.scalar_one_or_none()

        if profile is not None:
            LLMRouter.client_from_profile(profile)
            return ModelRuntime(
                router=LLMRouter(profile),
                profile_id=profile.id,
                provider=profile.provider,
                model=profile.model_name,
            )

        provider = self.settings.default_model_provider
        return ModelRuntime(
            router=LLMRouter(),
            profile_id=None,
            provider=provider,
            model="",
        )

    async def resolve_for_scene(
        self,
        scene_id: str,
        requested_profile_id: str | None,
    ) -> ModelRuntime:
        result = await self.session.execute(
            select(Volume.project_id)
            .select_from(Scene)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(Scene.id == scene_id)
        )
        project_id = result.scalar_one_or_none()
        if project_id is None:
            raise ModelConfigurationError(
                "scene not found while resolving model profile",
                {"scene_id": scene_id},
            )
        return await self.resolve(project_id, requested_profile_id)

    async def resolve_for_version(
        self,
        scene_version_id: str,
        requested_profile_id: str | None,
    ) -> ModelRuntime:
        result = await self.session.execute(
            select(Volume.project_id)
            .select_from(SceneVersion)
            .join(Scene, SceneVersion.scene_id == Scene.id)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(SceneVersion.id == scene_version_id)
        )
        project_id = result.scalar_one_or_none()
        if project_id is None:
            raise ModelConfigurationError(
                "scene version not found while resolving model profile",
                {"scene_version_id": scene_version_id},
            )
        return await self.resolve(project_id, requested_profile_id)

    async def _profile(self, profile_id: str) -> ModelProfile:
        profile = await self.session.get(ModelProfile, profile_id)
        if profile is None:
            raise ModelConfigurationError(
                "model profile not found",
                {"profile_id": profile_id},
            )
        if not profile.enabled:
            raise ModelConfigurationError(
                "model profile is disabled",
                {"profile_id": profile_id},
            )
        return profile
