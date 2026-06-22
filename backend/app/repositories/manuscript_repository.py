from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.repositories.base import Repository


class VolumeRepository(Repository[Volume]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Volume)

    async def list_by_project(self, project_id: str) -> list[Volume]:
        return await self.list(
            select(Volume).where(Volume.project_id == project_id).order_by(Volume.sequence_no)
        )


class ChapterRepository(Repository[Chapter]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Chapter)

    async def list_by_volume(self, volume_id: str) -> list[Chapter]:
        return await self.list(
            select(Chapter).where(Chapter.volume_id == volume_id).order_by(Chapter.sequence_no)
        )


class SceneRepository(Repository[Scene]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Scene)

    async def list_by_chapter(self, chapter_id: str) -> list[Scene]:
        return await self.list(
            select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.sequence_no)
        )


class SceneVersionRepository(Repository[SceneVersion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SceneVersion)

    async def list_by_scene(self, scene_id: str) -> list[SceneVersion]:
        return await self.list(
            select(SceneVersion)
            .where(SceneVersion.scene_id == scene_id)
            .order_by(SceneVersion.version_no.desc())
        )

    async def next_version_no(self, scene_id: str) -> int:
        result = await self.session.execute(
            select(func.max(SceneVersion.version_no)).where(SceneVersion.scene_id == scene_id)
        )
        return int(result.scalar_one_or_none() or 0) + 1
