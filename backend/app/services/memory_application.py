from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.canon.query import CanonQueryService
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.bible import CharacterRelationship
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.memory import MemoryCandidate, TimelineEvent
from app.models.world import WorldEntry
from app.schemas.memory import (
    CharacterKnowledgeMemoryItem,
    CharacterStateMemoryItem,
    MemoryItem,
    MemoryItemValue,
    RelationshipChangeMemoryItem,
    TimelineEventMemoryItem,
    WorldFactUpdateMemoryItem,
)


@dataclass(frozen=True)
class SceneMetadata:
    project_id: str
    timeline_order: int
    canon_version_id: str | None


class MemoryHandler(Protocol):
    async def apply(
        self,
        session: AsyncSession,
        candidate: MemoryCandidate,
        metadata: SceneMetadata,
        item: MemoryItemValue,
    ) -> None: ...


async def require_characters_in_project(
    session: AsyncSession,
    character_ids: list[str],
    project_id: str,
) -> None:
    unique_ids = set(character_ids)
    if not unique_ids:
        return
    result = await session.execute(
        select(Character.id).where(
            Character.id.in_(unique_ids),
            Character.project_id == project_id,
        )
    )
    found_ids = set(result.scalars().all())
    if found_ids != unique_ids:
        raise ValidationAppError(
            "memory candidate target character is not in the scene project",
            {"target_entity_ids": sorted(unique_ids - found_ids)},
        )


class CharacterStateHandler:
    async def apply(
        self,
        session: AsyncSession,
        candidate: MemoryCandidate,
        metadata: SceneMetadata,
        item: MemoryItemValue,
    ) -> None:
        if not isinstance(item, CharacterStateMemoryItem):
            raise ValidationAppError("invalid character state candidate")
        character_id = item.target_entity_id
        await require_characters_in_project(session, [character_id], metadata.project_id)
        result = await session.execute(
            select(CharacterState)
            .where(
                CharacterState.character_id == character_id,
                CharacterState.source_scene_version_id == candidate.scene_version_id,
            )
            .limit(1)
        )
        state = result.scalar_one_or_none()
        content = item.content_json
        values = {
            "timeline_order": metadata.timeline_order,
            "physical_state_json": content.physical_state,
            "emotional_state": content.emotional_state,
            "current_goal": content.current_goal,
            "current_pressure": content.current_pressure,
            "resources_json": content.resources,
            "injuries_json": content.injuries,
            "active_secrets_json": content.active_secrets,
            "notes": candidate.evidence,
            "status": "confirmed",
        }
        if state is None:
            session.add(
                CharacterState(
                    character_id=character_id,
                    source_scene_version_id=candidate.scene_version_id,
                    source_candidate_id=candidate.id,
                    **values,
                )
            )
            return
        for field, value in values.items():
            setattr(state, field, value)


class CharacterKnowledgeHandler:
    async def apply(
        self,
        session: AsyncSession,
        candidate: MemoryCandidate,
        metadata: SceneMetadata,
        item: MemoryItemValue,
    ) -> None:
        if not isinstance(item, CharacterKnowledgeMemoryItem):
            raise ValidationAppError("invalid character knowledge candidate")
        character_id = item.target_entity_id
        await require_characters_in_project(session, [character_id], metadata.project_id)
        content = item.content_json
        result = await session.execute(
            select(CharacterKnowledge)
            .where(
                CharacterKnowledge.character_id == character_id,
                CharacterKnowledge.fact_key == content.fact_key,
                CharacterKnowledge.learned_at_scene_version_id == candidate.scene_version_id,
            )
            .limit(1)
        )
        knowledge = result.scalar_one_or_none()
        values = {
            "fact_value_json": content.fact_value_json,
            "knowledge_status": content.knowledge_status,
            "confidence": candidate.confidence,
        }
        if knowledge is None:
            session.add(
                CharacterKnowledge(
                    character_id=character_id,
                    fact_key=content.fact_key,
                    learned_at_scene_version_id=candidate.scene_version_id,
                    source_candidate_id=candidate.id,
                    **values,
                )
            )
            return
        for field, value in values.items():
            setattr(knowledge, field, value)


class TimelineEventHandler:
    async def apply(
        self,
        session: AsyncSession,
        candidate: MemoryCandidate,
        metadata: SceneMetadata,
        item: MemoryItemValue,
    ) -> None:
        if not isinstance(item, TimelineEventMemoryItem):
            raise ValidationAppError("invalid timeline event candidate")
        content = item.content_json
        await require_characters_in_project(
            session,
            content.affected_character_ids,
            metadata.project_id,
        )
        result = await session.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.project_id == metadata.project_id,
                TimelineEvent.scene_version_id == candidate.scene_version_id,
                TimelineEvent.event_text == content.event_text,
            )
            .limit(1)
        )
        event = result.scalar_one_or_none()
        if event is None:
            session.add(
                TimelineEvent(
                    project_id=metadata.project_id,
                    scene_version_id=candidate.scene_version_id,
                    event_text=content.event_text,
                    timeline_order=metadata.timeline_order,
                    affected_character_ids=content.affected_character_ids,
                    source_candidate_id=candidate.id,
                )
            )
            return
        event.timeline_order = metadata.timeline_order
        event.affected_character_ids = content.affected_character_ids


class RelationshipChangeHandler:
    async def apply(
        self,
        session: AsyncSession,
        candidate: MemoryCandidate,
        metadata: SceneMetadata,
        item: MemoryItemValue,
    ) -> None:
        if not isinstance(item, RelationshipChangeMemoryItem):
            raise ValidationAppError("invalid relationship change candidate")
        content = item.content_json
        await require_characters_in_project(
            session,
            [content.character_a_id, content.character_b_id],
            metadata.project_id,
        )
        result = await session.execute(
            select(CharacterRelationship)
            .where(
                CharacterRelationship.project_id == metadata.project_id,
                CharacterRelationship.character_a_id == content.character_a_id,
                CharacterRelationship.character_b_id == content.character_b_id,
                CharacterRelationship.relation_type == content.relation_type,
            )
            .limit(1)
        )
        relationship = result.scalar_one_or_none()
        if relationship is None:
            session.add(
                CharacterRelationship(
                    project_id=metadata.project_id,
                    character_a_id=content.character_a_id,
                    character_b_id=content.character_b_id,
                    relation_type=content.relation_type,
                    description=content.description,
                    timeline_info=content.timeline_info,
                    status="active",
                    source_scene_version_id=candidate.scene_version_id,
                    source_candidate_id=candidate.id,
                )
            )
            return
        relationship.description = content.description
        relationship.timeline_info = content.timeline_info
        relationship.status = "active"


class WorldFactUpdateHandler:
    async def apply(
        self,
        session: AsyncSession,
        candidate: MemoryCandidate,
        metadata: SceneMetadata,
        item: MemoryItemValue,
    ) -> None:
        if not isinstance(item, WorldFactUpdateMemoryItem):
            raise ValidationAppError("invalid world fact update candidate")
        entry = await session.get(WorldEntry, item.target_entity_id)
        if entry is None or entry.project_id != metadata.project_id:
            raise ValidationAppError(
                "memory candidate target world entry is not in the scene project",
                {"target_entity_id": item.target_entity_id},
            )
        updates = item.content_json.model_dump(exclude_unset=True, exclude_none=True)
        changed = False
        for field, value in updates.items():
            if getattr(entry, field) != value:
                setattr(entry, field, value)
                changed = True
        if changed:
            entry.version += 1
        entry.source_scene_version_id = candidate.scene_version_id
        entry.source_candidate_id = candidate.id


HANDLERS: dict[str, MemoryHandler] = {
    "character_state": CharacterStateHandler(),
    "character_knowledge": CharacterKnowledgeHandler(),
    "timeline_event": TimelineEventHandler(),
    "relationship_change": RelationshipChangeHandler(),
    "world_fact_update": WorldFactUpdateHandler(),
}


class MemoryApplicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def apply(self, candidate: MemoryCandidate) -> None:
        item = self._validate(candidate)
        metadata = await self._scene_metadata(candidate.scene_version_id)
        if metadata.canon_version_id != candidate.scene_version_id:
            raise ConflictError(
                "memory candidate source is not the current Canon version",
                {
                    "reason": "CANDIDATE_SOURCE_NOT_APPROVED",
                    "scene_version_id": candidate.scene_version_id,
                },
            )
        handler = HANDLERS.get(candidate.candidate_type)
        if handler is None:
            raise ValidationAppError(
                "unsupported memory candidate type",
                {"candidate_type": candidate.candidate_type},
            )
        await handler.apply(self.session, candidate, metadata, item)

    def _validate(self, candidate: MemoryCandidate) -> MemoryItemValue:
        try:
            return MemoryItem.model_validate(
                {
                    "candidate_type": candidate.candidate_type,
                    "target_entity_type": candidate.target_entity_type,
                    "target_entity_id": candidate.target_entity_id,
                    "content_json": candidate.content_json,
                    "evidence": candidate.evidence,
                    "confidence": candidate.confidence,
                }
            ).root
        except ValidationError:
            raise ValidationAppError(
                "invalid memory candidate content",
                {"candidate_type": candidate.candidate_type},
            ) from None

    async def _scene_metadata(self, scene_version_id: str) -> SceneMetadata:
        result = await self.session.execute(
            select(
                Volume.project_id,
                Scene.id.label("scene_id"),
                Scene.story_time_order,
            )
            .select_from(SceneVersion)
            .join(Scene, SceneVersion.scene_id == Scene.id)
            .join(Chapter, Scene.chapter_id == Chapter.id)
            .join(Volume, Chapter.volume_id == Volume.id)
            .where(SceneVersion.id == scene_version_id)
        )
        row = result.one_or_none()
        if row is None:
            raise NotFoundError(
                "scene version not found",
                {"version_id": scene_version_id},
            )
        canon = await CanonQueryService(self.session).get_scene_version(row.scene_id)
        return SceneMetadata(
            project_id=row.project_id,
            timeline_order=row.story_time_order,
            canon_version_id=canon.version.id if canon is not None else None,
        )
