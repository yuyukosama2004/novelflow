from __future__ import annotations

from sqlalchemy import and_, delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.canon.query import CanonQueryService
from app.canon.service import CanonService
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.documents.codec import SceneDocument, SceneDocumentError, build_scene_document
from app.models.base import utc_now
from app.models.bible import CharacterRelationship
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import (
    Chapter,
    ImpactReport,
    Scene,
    SceneCharacter,
    SceneVersion,
    SceneWorkingDraft,
    SceneWorldEntry,
    Volume,
)
from app.models.memory import MemoryCandidate, MemoryExtractionRun, TimelineEvent
from app.models.review import ReviewIssue, ReviewRun
from app.models.world import WorldEntry
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
    SceneWorkingDraftUpdate,
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
        values = payload.model_dump()
        story_time_order = values.pop("story_time_order")
        if story_time_order is None:
            story_time_order = await self._default_story_time_order(
                chapter_id,
                payload.sequence_no,
            )
        scene = Scene(
            chapter_id=chapter_id,
            story_time_order=story_time_order,
            **values,
        )
        await self.scenes.add(scene)
        await self.session.commit()
        return scene

    async def _default_story_time_order(
        self,
        chapter_id: str,
        scene_sequence_no: int,
    ) -> int:
        position_result = await self.session.execute(
            select(
                Chapter.sequence_no.label("chapter_sequence_no"),
                Volume.sequence_no.label("volume_sequence_no"),
                Volume.project_id.label("project_id"),
            )
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(Chapter.id == chapter_id)
        )
        position = position_result.one()
        previous_result = await self.session.execute(
            select(Scene.story_time_order)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(
                Volume.project_id == position.project_id,
                or_(
                    Volume.sequence_no < position.volume_sequence_no,
                    and_(
                        Volume.sequence_no == position.volume_sequence_no,
                        Chapter.sequence_no < position.chapter_sequence_no,
                    ),
                    and_(
                        Volume.sequence_no == position.volume_sequence_no,
                        Chapter.sequence_no == position.chapter_sequence_no,
                        Scene.sequence_no < scene_sequence_no,
                    ),
                ),
            )
            .order_by(
                Volume.sequence_no.desc(),
                Chapter.sequence_no.desc(),
                Scene.sequence_no.desc(),
            )
            .limit(1)
        )
        previous_order = previous_result.scalar_one_or_none()
        return (previous_order + 1) if previous_order is not None else 1

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

    async def get_context_links(self, scene_id: str) -> tuple[list[str], list[str]]:
        await self.get_scene(scene_id)
        character_result = await self.session.execute(
            select(SceneCharacter.character_id).where(SceneCharacter.scene_id == scene_id)
        )
        world_result = await self.session.execute(
            select(SceneWorldEntry.world_entry_id).where(SceneWorldEntry.scene_id == scene_id)
        )
        return (
            list(character_result.scalars().all()),
            list(world_result.scalars().all()),
        )

    async def replace_context_links(
        self,
        scene_id: str,
        character_ids: list[str],
        world_entry_ids: list[str],
    ) -> tuple[list[str], list[str]]:
        scene = await self.get_scene(scene_id)
        project_result = await self.session.execute(
            select(Volume.project_id)
            .join(Chapter, Chapter.volume_id == Volume.id)
            .where(Chapter.id == scene.chapter_id)
        )
        project_id = project_result.scalar_one()
        requested_characters = set(character_ids)
        requested_world = set(world_entry_ids)
        valid_characters = set(
            (
                await self.session.execute(
                    select(Character.id).where(
                        Character.project_id == project_id,
                        Character.id.in_(requested_characters),
                    )
                )
            )
            .scalars()
            .all()
        )
        valid_world = set(
            (
                await self.session.execute(
                    select(WorldEntry.id).where(
                        WorldEntry.project_id == project_id,
                        WorldEntry.id.in_(requested_world),
                    )
                )
            )
            .scalars()
            .all()
        )
        if valid_characters != requested_characters or valid_world != requested_world:
            raise ValidationAppError(
                "context links must belong to the scene project",
                {
                    "reason": "CONTEXT_LINK_PROJECT_MISMATCH",
                    "invalid_character_ids": sorted(requested_characters - valid_characters),
                    "invalid_world_entry_ids": sorted(requested_world - valid_world),
                },
            )
        await self.session.execute(delete(SceneCharacter).where(SceneCharacter.scene_id == scene_id))
        await self.session.execute(delete(SceneWorldEntry).where(SceneWorldEntry.scene_id == scene_id))
        self.session.add_all(
            [
                SceneCharacter(scene_id=scene_id, character_id=character_id)
                for character_id in sorted(requested_characters)
            ]
            + [
                SceneWorldEntry(scene_id=scene_id, world_entry_id=world_entry_id)
                for world_entry_id in sorted(requested_world)
            ]
        )
        await self.session.commit()
        return sorted(requested_characters), sorted(requested_world)

    async def delete_scene(self, scene_id: str) -> None:
        await self.get_scene(scene_id)
        if await CanonQueryService(self.session).get_scene_version(scene_id) is not None:
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
        document = self._build_version_document(payload)
        version = SceneVersion(
            scene_id=scene_id,
            version_no=await self.versions.next_version_no(scene_id),
            **payload.model_dump(exclude={"content_json", "content_markdown"}),
            content_json=document.content_json,
            content_markdown=document.content_markdown,
            content_text=document.content_text,
            document_schema_version=document.schema_version,
            document_hash=document.document_hash,
        )
        await self.versions.add(version)
        await self.session.commit()
        return version

    @staticmethod
    def _build_version_document(payload: SceneVersionCreate) -> SceneDocument:
        try:
            return build_scene_document(
                content_json=(payload.content_json if "content_json" in payload.model_fields_set else None),
                content_markdown=(
                    payload.content_markdown if "content_markdown" in payload.model_fields_set else None
                ),
            )
        except SceneDocumentError as exc:
            raise ValidationAppError(
                "scene document representations do not match",
                {
                    "reason": "DOCUMENT_REPRESENTATION_MISMATCH",
                    "message": str(exc),
                },
            ) from exc

    async def list_versions(self, scene_id: str) -> list[SceneVersion]:
        await self.get_scene(scene_id)
        return await self.versions.list_by_scene(scene_id)

    async def get_version(self, version_id: str) -> SceneVersion:
        version = await self.versions.get(version_id)
        if version is None:
            raise NotFoundError("scene version not found", {"version_id": version_id})
        return version

    async def get_working_draft(self, scene_id: str) -> SceneWorkingDraft | None:
        await self.get_scene(scene_id)
        result = await self.session.execute(
            select(SceneWorkingDraft).where(SceneWorkingDraft.scene_id == scene_id)
        )
        return result.scalar_one_or_none()

    async def update_working_draft(
        self,
        scene_id: str,
        payload: SceneWorkingDraftUpdate,
    ) -> SceneWorkingDraft:
        await self.get_scene(scene_id)
        try:
            document = build_scene_document(
                content_json=payload.content_json,
                content_markdown=payload.content_markdown,
            )
        except SceneDocumentError as exc:
            raise ValidationAppError(
                "scene document representations do not match",
                {
                    "reason": "DOCUMENT_REPRESENTATION_MISMATCH",
                    "message": str(exc),
                },
            ) from exc
        existing = await self.get_working_draft(scene_id)
        if existing is None:
            if payload.revision != 0:
                raise ConflictError(
                    "working draft revision conflict",
                    {"reason": "DRAFT_REVISION_CONFLICT", "current_revision": 0},
                )
            draft = SceneWorkingDraft(
                scene_id=scene_id,
                content_json=document.content_json,
                content_markdown=document.content_markdown,
                revision=1,
            )
            self.session.add(draft)
            try:
                await self.session.commit()
            except IntegrityError:
                await self.session.rollback()
                current = await self.get_working_draft(scene_id)
                raise ConflictError(
                    "working draft revision conflict",
                    {
                        "reason": "DRAFT_REVISION_CONFLICT",
                        "current_revision": current.revision if current else 0,
                    },
                ) from None
            await self.session.refresh(draft)
            return draft

        result = await self.session.execute(
            update(SceneWorkingDraft)
            .where(
                SceneWorkingDraft.scene_id == scene_id,
                SceneWorkingDraft.revision == payload.revision,
            )
            .values(
                content_json=document.content_json,
                content_markdown=document.content_markdown,
                revision=payload.revision + 1,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            await self.session.rollback()
            current = await self.get_working_draft(scene_id)
            raise ConflictError(
                "working draft revision conflict",
                {
                    "reason": "DRAFT_REVISION_CONFLICT",
                    "current_revision": current.revision if current else 0,
                },
            )
        await self.session.commit()
        updated = await self.get_working_draft(scene_id)
        if updated is None:  # pragma: no cover - guarded by the update above
            raise NotFoundError("working draft not found", {"scene_id": scene_id})
        return updated

    async def approve_version(self, scene_id: str, payload: ApproveVersionRequest) -> Scene:
        scene = await self.get_scene(scene_id)
        version = await self.get_version(payload.version_id)
        if version.scene_id != scene_id:
            raise ConflictError(
                "version does not belong to scene",
                {"reason": "VERSION_SCENE_MISMATCH"},
            )
        if not version.content_text.strip():
            raise ValidationAppError(
                "version content is empty",
                {"reason": "EMPTY_VERSION_CONTENT"},
            )
        current_canon = await CanonQueryService(self.session).get_scene_version(scene_id)
        if current_canon is not None and current_canon.version.id == version.id:
            if scene.approved_version_id != version.id:
                scene.approved_version_id = version.id
                await self.session.commit()
                await self.session.refresh(scene)
            return scene
        old_version = current_canon.version if current_canon is not None else None

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

        issue_result = await self.session.execute(
            select(ReviewIssue).where(ReviewIssue.review_run_id == review_run.id).order_by(ReviewIssue.id)
        )
        review_issues = list(issue_result.scalars().all())
        blocking_issues = [
            issue
            for issue in review_issues
            if issue.severity == "blocking" and issue.status != "false_positive"
        ]
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
        chapter = await self.get_chapter(scene.chapter_id)
        volume = await self.get_volume(chapter.volume_id)
        if old_version is None:
            chapter.approved_word_count += sum(not character.isspace() for character in version.content_text)
        else:
            chapter.approved_word_count = max(
                0,
                chapter.approved_word_count
                - sum(not character.isspace() for character in old_version.content_text)
                + sum(not character.isspace() for character in version.content_text),
            )
            old_version.superseded_at = utc_now()
            old_version.superseded_by_version_id = version.id
            await self._invalidate_version_memory(old_version.id)
            affected_scenes, project_id = await self._mark_later_scenes_stale(scene)
            self.session.add(
                ImpactReport(
                    project_id=project_id,
                    source_scene_id=scene.id,
                    old_version_id=old_version.id,
                    new_version_id=version.id,
                    affected_scene_ids_json=[item.id for item in affected_scenes],
                    reason_json={"reason": "CANONICAL_VERSION_REPLACED"},
                    status="open",
                )
            )
        await CanonService(self.session).record_scene_approval(
            project_id=volume.project_id,
            scene=scene,
            version=version,
            review_run=review_run,
            review_issues=review_issues,
            override_reason=version.approval_override_reason,
        )
        await self.session.commit()
        await self.session.refresh(scene)
        return scene

    async def _invalidate_version_memory(self, version_id: str) -> None:
        await self.session.execute(
            update(MemoryCandidate)
            .where(
                MemoryCandidate.scene_version_id == version_id,
                MemoryCandidate.status == "pending",
            )
            .values(status="invalidated")
        )
        await self.session.execute(
            update(CharacterState)
            .where(CharacterState.source_scene_version_id == version_id)
            .values(status="invalidated")
        )
        await self.session.execute(
            update(CharacterKnowledge)
            .where(CharacterKnowledge.learned_at_scene_version_id == version_id)
            .values(record_status="invalidated")
        )
        await self.session.execute(
            update(TimelineEvent)
            .where(TimelineEvent.scene_version_id == version_id)
            .values(status="invalidated")
        )
        await self.session.execute(
            update(CharacterRelationship)
            .where(CharacterRelationship.source_scene_version_id == version_id)
            .values(status="invalidated")
        )
        await self.session.execute(
            update(WorldEntry)
            .where(WorldEntry.source_scene_version_id == version_id)
            .values(canon_status="invalidated")
        )

    async def _mark_later_scenes_stale(
        self,
        scene: Scene,
    ) -> tuple[list[Scene], str]:
        position_result = await self.session.execute(
            select(Chapter, Volume)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(Chapter.id == scene.chapter_id)
        )
        chapter, volume = position_result.one()
        later_result = await self.session.execute(
            select(Scene)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(
                Volume.project_id == volume.project_id,
                or_(
                    Volume.sequence_no > volume.sequence_no,
                    and_(
                        Volume.sequence_no == volume.sequence_no,
                        Chapter.sequence_no > chapter.sequence_no,
                    ),
                    and_(
                        Volume.sequence_no == volume.sequence_no,
                        Chapter.sequence_no == chapter.sequence_no,
                        Scene.sequence_no > scene.sequence_no,
                    ),
                ),
            )
        )
        later_scenes = list(later_result.scalars().all())
        for later_scene in later_scenes:
            later_scene.is_stale = True
        return later_scenes, volume.project_id

    async def list_impact_reports(self, project_id: str) -> list[ImpactReport]:
        await ProjectService(self.session).get(project_id)
        result = await self.session.execute(
            select(ImpactReport)
            .where(ImpactReport.project_id == project_id)
            .order_by(ImpactReport.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_impact_report(self, report_id: str, status: str) -> ImpactReport:
        report = await self.session.get(ImpactReport, report_id)
        if report is None:
            raise NotFoundError("impact report not found", {"report_id": report_id})
        report.status = status
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def clear_scene_stale(self, scene_id: str) -> Scene:
        scene = await self.get_scene(scene_id)
        scene.is_stale = False
        await self.session.commit()
        await self.session.refresh(scene)
        return scene

    async def complete_scene(self, scene_id: str) -> Scene:
        scene = await self.get_scene(scene_id)
        current_canon = await CanonQueryService(self.session).get_scene_version(scene_id)
        if current_canon is None:
            raise ConflictError(
                "scene has no approved version",
                {"reason": "APPROVED_VERSION_REQUIRED"},
            )
        canonical_version_id = current_canon.version.id

        extraction_result = await self.session.execute(
            select(MemoryExtractionRun)
            .where(
                MemoryExtractionRun.scene_version_id == canonical_version_id,
                MemoryExtractionRun.status == "completed",
            )
            .order_by(
                MemoryExtractionRun.completed_at.desc(),
                MemoryExtractionRun.created_at.desc(),
                MemoryExtractionRun.id.desc(),
            )
            .limit(1)
        )
        if extraction_result.scalar_one_or_none() is None:
            raise ConflictError(
                "memory extraction required",
                {"reason": "MEMORY_EXTRACTION_REQUIRED"},
            )

        pending_result = await self.session.execute(
            select(MemoryCandidate.id)
            .where(
                MemoryCandidate.scene_version_id == canonical_version_id,
                MemoryCandidate.status == "pending",
            )
            .limit(1)
        )
        if pending_result.scalar_one_or_none() is not None:
            raise ConflictError(
                "pending memory candidates must be resolved",
                {"reason": "PENDING_MEMORY_CANDIDATES"},
            )

        scene.status = "completed"
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
        return left, right, left.document_hash != right.document_hash
