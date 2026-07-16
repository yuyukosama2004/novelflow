from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.canon.query import CanonQueryService
from app.models.character import Character
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.world import WorldEntry
from app.services.project_service import ProjectService


class ExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def markdown(self, project_id: str) -> str:
        project = await ProjectService(self.session).get(project_id)
        lines = [f"# {project.title}", "", project.summary, ""]
        volumes = await self._volumes(project_id)
        for volume in volumes:
            lines.extend([f"## {volume.title}", "", volume.summary, ""])
            chapters = await self._chapters(volume.id)
            for chapter in chapters:
                lines.extend([f"### {chapter.title}", "", chapter.summary, ""])
                scenes = await self._scenes(chapter.id)
                canon_versions = await CanonQueryService(self.session).latest_versions_for_scenes(
                    [scene.id for scene in scenes]
                )
                for scene in scenes:
                    lines.extend([f"#### {scene.title}", ""])
                    canon = canon_versions.get(scene.id)
                    if canon is None:
                        lines.extend(["> No approved version.", ""])
                    else:
                        lines.extend([canon.version.content_markdown, ""])
        return "\n".join(lines).strip() + "\n"

    async def backup_json(self, project_id: str) -> dict[str, Any]:
        project = await ProjectService(self.session).get(project_id)
        volumes = await self._volumes(project_id)
        volume_ids = [volume.id for volume in volumes]
        chapters = await self._chapters_for_volumes(volume_ids)
        chapter_ids = [chapter.id for chapter in chapters]
        scenes = await self._scenes_for_chapters(chapter_ids)
        scene_ids = [scene.id for scene in scenes]
        versions = await self._versions_for_scenes(scene_ids)
        characters = await self._characters(project_id)
        world_entries = await self._world_entries(project_id)
        return {
            "project": self._dump(project),
            "characters": [self._dump(item) for item in characters],
            "world_entries": [self._dump(item) for item in world_entries],
            "volumes": [self._dump(item) for item in volumes],
            "chapters": [self._dump(item) for item in chapters],
            "scenes": [self._dump(item) for item in scenes],
            "scene_versions": [self._dump(item) for item in versions],
        }

    async def _volumes(self, project_id: str) -> list[Volume]:
        result = await self.session.execute(
            select(Volume).where(Volume.project_id == project_id).order_by(Volume.sequence_no)
        )
        return list(result.scalars().all())

    async def _chapters(self, volume_id: str) -> list[Chapter]:
        result = await self.session.execute(
            select(Chapter).where(Chapter.volume_id == volume_id).order_by(Chapter.sequence_no)
        )
        return list(result.scalars().all())

    async def _scenes(self, chapter_id: str) -> list[Scene]:
        result = await self.session.execute(
            select(Scene).where(Scene.chapter_id == chapter_id).order_by(Scene.sequence_no)
        )
        return list(result.scalars().all())

    async def _chapters_for_volumes(self, volume_ids: list[str]) -> list[Chapter]:
        if not volume_ids:
            return []
        result = await self.session.execute(
            select(Chapter).where(Chapter.volume_id.in_(volume_ids)).order_by(Chapter.sequence_no)
        )
        return list(result.scalars().all())

    async def _scenes_for_chapters(self, chapter_ids: list[str]) -> list[Scene]:
        if not chapter_ids:
            return []
        result = await self.session.execute(
            select(Scene).where(Scene.chapter_id.in_(chapter_ids)).order_by(Scene.sequence_no)
        )
        return list(result.scalars().all())

    async def _versions_for_scenes(self, scene_ids: list[str]) -> list[SceneVersion]:
        if not scene_ids:
            return []
        result = await self.session.execute(
            select(SceneVersion)
            .where(SceneVersion.scene_id.in_(scene_ids))
            .order_by(SceneVersion.scene_id, SceneVersion.version_no)
        )
        return list(result.scalars().all())

    async def _characters(self, project_id: str) -> list[Character]:
        result = await self.session.execute(
            select(Character).where(Character.project_id == project_id).order_by(Character.name)
        )
        return list(result.scalars().all())

    async def _world_entries(self, project_id: str) -> list[WorldEntry]:
        result = await self.session.execute(
            select(WorldEntry).where(WorldEntry.project_id == project_id).order_by(WorldEntry.name)
        )
        return list(result.scalars().all())

    def _dump(self, item: Any) -> dict[str, Any]:
        data = dict(item.__dict__)
        data.pop("_sa_instance_state", None)
        for key, value in list(data.items()):
            if hasattr(value, "isoformat"):
                data[key] = value.isoformat()
        return data
