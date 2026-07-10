from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.models.base import utc_now
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.review import ReviewIssue, ReviewRun
from app.repositories.base import apply_updates
from app.repositories.manuscript_repository import (
    ChapterRepository,
    SceneRepository,
    SceneVersionRepository,
    VolumeRepository,
)
from app.schemas.manuscript import (
    ApproveVersionRequest,
    ChapterCreate,
    ChapterUpdate,
    SceneCreate,
    SceneReorderRequest,
    SceneUpdate,
    SceneVersionCreate,
    VolumeCreate,
    VolumeUpdate,
)
from app.services.project_service import ProjectService


class ManuscriptService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.volumes = VolumeRepository(session)
        self.chapters = ChapterRepository(session)
        self.scenes = SceneRepository(session)
        self.versions = SceneVersionRepository(session)

    async def create_volume(self, project_id: str, payload: VolumeCreate) -> Volume:
        await ProjectService(self.session).get(project_id)
        volume = Volume(project_id=project_id, **payload.model_dump())
        await self.volumes.add(volume)
        await self.session.commit()
        return volume

    async def list_volumes(self, project_id: str) -> list[Volume]:
        await ProjectService(self.session).get(project_id)
        return await self.volumes.list_by_project(project_id)

    async def get_volume(self, volume_id: str) -> Volume:
        volume = await self.volumes.get(volume_id)
        if volume is None:
            raise NotFoundError("volume not found", {"volume_id": volume_id})
        return volume

    async def update_volume(self, volume_id: str, payload: VolumeUpdate) -> Volume:
        volume = await self.get_volume(volume_id)
        apply_updates(volume, payload.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.session.refresh(volume)
        return volume

    async def create_chapter(self, volume_id: str, payload: ChapterCreate) -> Chapter:
        await self.get_volume(volume_id)
        chapter = Chapter(volume_id=volume_id, **payload.model_dump())
        await self.chapters.add(chapter)
        await self.session.commit()
        return chapter

    async def list_chapters(self, volume_id: str) -> list[Chapter]:
        await self.get_volume(volume_id)
        return await self.chapters.list_by_volume(volume_id)

    async def get_chapter(self, chapter_id: str) -> Chapter:
        chapter = await self.chapters.get(chapter_id)
        if chapter is None:
            raise NotFoundError("chapter not found", {"chapter_id": chapter_id})
        return chapter

    async def update_chapter(self, chapter_id: str, payload: ChapterUpdate) -> Chapter:
        chapter = await self.get_chapter(chapter_id)
        apply_updates(chapter, payload.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.session.refresh(chapter)
        return chapter

    async def create_scene(self, chapter_id: str, payload: SceneCreate) -> Scene:
        await self.get_chapter(chapter_id)
        scene = Scene(chapter_id=chapter_id, **payload.model_dump())
        await self.scenes.add(scene)
        await self.session.commit()
        return scene

    async def list_scenes(self, chapter_id: str) -> list[Scene]:
        await self.get_chapter(chapter_id)
        return await self.scenes.list_by_chapter(chapter_id)

    async def get_scene(self, scene_id: str) -> Scene:
        scene = await self.scenes.get(scene_id)
        if scene is None:
            raise NotFoundError("scene not found", {"scene_id": scene_id})
        return scene

    async def update_scene(self, scene_id: str, payload: SceneUpdate) -> Scene:
        scene = await self.get_scene(scene_id)
        apply_updates(scene, payload.model_dump(exclude_unset=True))
        await self.session.commit()
        await self.session.refresh(scene)
        return scene

    async def delete_scene(self, scene_id: str) -> None:
        scene = await self.get_scene(scene_id)
        if scene.approved_version_id:
            raise ConflictError("approved scene cannot be deleted", {"scene_id": scene_id})
        await self.scenes.delete(scene_id)
        await self.session.commit()

    async def reorder_scenes(self, payload: SceneReorderRequest) -> list[Scene]:
        existing = {scene.id: scene for scene in await self.list_scenes(payload.chapter_id)}
        if set(existing) != {item.scene_id for item in payload.items}:
            raise ConflictError("reorder items must match chapter scenes")
        for item in payload.items:
            existing[item.scene_id].sequence_no = item.sequence_no
        await self.session.commit()
        return await self.list_scenes(payload.chapter_id)

    async def create_version(self, scene_id: str, payload: SceneVersionCreate) -> SceneVersion:
        await self.get_scene(scene_id)
        version = SceneVersion(
            scene_id=scene_id,
            version_no=await self.versions.next_version_no(scene_id),
            **payload.model_dump(),
        )
        await self.versions.add(version)
        await self.session.commit()
        return version

    async def list_versions(self, scene_id: str) -> list[SceneVersion]:
        await self.get_scene(scene_id)
        return await self.versions.list_by_scene(scene_id)

    async def get_version(self, version_id: str) -> SceneVersion:
        version = await self.versions.get(version_id)
        if version is None:
            raise NotFoundError("scene version not found", {"version_id": version_id})
        return version

    async def approve_version(self, scene_id: str, payload: ApproveVersionRequest) -> Scene:
        scene = await self.get_scene(scene_id)
        version = await self.get_version(payload.version_id)
        if version.scene_id != scene_id:
            raise ConflictError(
                "version does not belong to scene",
                {"reason": "VERSION_SCENE_MISMATCH"},
            )
        if not version.content_markdown.strip():
            raise ValidationAppError(
                "version content is empty",
                {"reason": "EMPTY_VERSION_CONTENT"},
            )
        if scene.approved_version_id == version.id:
            return scene
        if scene.approved_version_id is not None:
            raise ConflictError(
                "historical replacement is not ready",
                {"reason": "HISTORICAL_REPLACEMENT_NOT_READY"},
            )

        review_result = await self.session.execute(
            select(ReviewRun)
            .where(
                ReviewRun.scene_version_id == version.id,
                ReviewRun.status == "completed",
            )
            .order_by(
                ReviewRun.completed_at.desc(),
                ReviewRun.created_at.desc(),
                ReviewRun.id.desc(),
            )
            .limit(1)
        )
        review_run = review_result.scalar_one_or_none()
        if review_run is None:
            raise ConflictError(
                "version review required",
                {"reason": "VERSION_REVIEW_REQUIRED"},
            )

        blocking_result = await self.session.execute(
            select(ReviewIssue).where(
                ReviewIssue.review_run_id == review_run.id,
                ReviewIssue.severity == "blocking",
                ReviewIssue.status != "false_positive",
            )
        )
        blocking_issues = list(blocking_result.scalars().all())
        override_reason = (payload.override_reason or "").strip()
        if blocking_issues and not override_reason:
            raise ConflictError(
                "blocking review issues require an override reason",
                {
                    "reason": "BLOCKING_REVIEW_ISSUES",
                    "review_run_id": review_run.id,
                    "issue_count": len(blocking_issues),
                },
            )

        scene.approved_version_id = version.id
        scene.status = "canonicalizing"
        version.approved_at = utc_now()
        version.approval_override_reason = override_reason if blocking_issues else None
        await self.session.commit()
        await self.session.refresh(scene)
        return scene

    async def compare_versions(
        self,
        scene_id: str,
        left_id: str,
        right_id: str,
    ) -> tuple[SceneVersion, SceneVersion, bool]:
        await self.get_scene(scene_id)
        left = await self.get_version(left_id)
        right = await self.get_version(right_id)
        if left.scene_id != scene_id or right.scene_id != scene_id:
            raise ConflictError("versions must belong to scene")
        return left, right, left.content_markdown != right.content_markdown
