from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.core.responses import success
from app.database.session import get_session
from app.llm.router import LLMRouter
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.memory import MemoryCandidate, TimelineEvent
from app.services.context_builder import ContextBuilder
from app.services.manuscript_service import ManuscriptService
from app.services.memory_curator import MemoryCurator

router = APIRouter()


class MemoryCandidateOut(BaseModel):
    id: str
    scene_version_id: str
    candidate_type: str
    target_entity_type: str
    target_entity_id: str | None
    content_json: dict
    evidence: str
    confidence: float
    status: str

    model_config = {"from_attributes": True}


class UpdateCandidateRequest(BaseModel):
    status: Literal["approved", "rejected"]
    content_json: dict | None = None


@router.post("/scene-versions/{version_id}/extract-memories")
async def extract_memories(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Extract memory candidates from a scene version."""
    settings = get_settings()
    manuscript = ManuscriptService(session)
    version = await manuscript.get_version(version_id)

    builder = ContextBuilder(session)
    ctx = await builder.build_for_scene(version.scene_id)

    curator = MemoryCurator(LLMRouter(), settings.default_model_provider)
    candidates = await curator.extract(version, ctx)

    for candidate in candidates:
        session.add(candidate)
    await session.commit()

    return success(
        [MemoryCandidateOut.model_validate(c) for c in candidates],
        request,
    )


@router.get("/scene-versions/{version_id}/candidates")
async def list_candidates(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List memory candidates for a scene version."""
    result = await session.execute(
        select(MemoryCandidate)
        .where(MemoryCandidate.scene_version_id == version_id)
        .order_by(MemoryCandidate.confidence.desc())
    )
    candidates = result.scalars().all()
    return success(
        [MemoryCandidateOut.model_validate(c) for c in candidates],
        request,
    )


@router.patch("/candidates/{candidate_id}")
async def update_candidate(
    candidate_id: str,
    payload: UpdateCandidateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Approve or reject a memory candidate. On approval, apply state changes."""
    candidate = await session.get(MemoryCandidate, candidate_id)
    if candidate is None:
        raise NotFoundError("candidate not found", {"candidate_id": candidate_id})

    if candidate.status == payload.status and payload.content_json is None:
        return success(MemoryCandidateOut.model_validate(candidate), request)
    if candidate.status != "pending":
        raise ConflictError(
            "memory candidate has already been resolved",
            {"candidate_id": candidate_id, "status": candidate.status},
        )

    if payload.content_json is not None:
        candidate.content_json = payload.content_json

    if payload.status == "approved":
        await _apply_candidate(session, candidate)

    candidate.status = payload.status
    await session.commit()
    return success(MemoryCandidateOut.model_validate(candidate), request)


async def _apply_candidate(session: AsyncSession, candidate: MemoryCandidate) -> None:
    """Apply an approved memory candidate to the relevant entity."""
    project_id, timeline_order = await _scene_metadata(
        session,
        candidate.scene_version_id,
    )

    if candidate.candidate_type in ("character_state", "character_knowledge"):
        char_id = candidate.target_entity_id
        if not char_id:
            raise ValidationAppError("character memory candidate requires target_entity_id")
        character = await session.get(Character, char_id)
        if character is None or character.project_id != project_id:
            raise ValidationAppError(
                "memory candidate target character is not in the scene project",
                {"target_entity_id": char_id},
            )

        if candidate.candidate_type == "character_state":
            session.add(
                CharacterState(
                    character_id=char_id,
                    timeline_order=timeline_order,
                    physical_state_json=candidate.content_json.get("physical_state", {}),
                    emotional_state=candidate.content_json.get("emotional_state", ""),
                    current_goal=candidate.content_json.get("current_goal", ""),
                    current_pressure=candidate.content_json.get("current_pressure", ""),
                    resources_json=candidate.content_json.get("resources", {}),
                    injuries_json=candidate.content_json.get("injuries", {}),
                    active_secrets_json=candidate.content_json.get("active_secrets", []),
                    notes=candidate.evidence,
                    source_scene_version_id=candidate.scene_version_id,
                    status="confirmed",
                )
            )
            return

        fact_key = candidate.content_json.get("fact_key")
        if not isinstance(fact_key, str) or not fact_key.strip():
            raise ValidationAppError("character knowledge candidate requires fact_key")
        knowledge_status = candidate.content_json.get(
            "knowledge_status",
            "confirmed",
        )
        allowed_statuses = {
            "unknown",
            "suspected",
            "believed",
            "confirmed",
            "misunderstood",
            "forgotten",
        }
        if knowledge_status not in allowed_statuses:
            raise ValidationAppError(
                "invalid character knowledge status",
                {"knowledge_status": knowledge_status},
            )
        fact_value = candidate.content_json.get(
            "fact_value_json",
            candidate.content_json.get("fact_value", {}),
        )
        if not isinstance(fact_value, dict):
            fact_value = {"value": fact_value}
        session.add(
            CharacterKnowledge(
                character_id=char_id,
                fact_key=fact_key.strip(),
                fact_value_json=fact_value,
                knowledge_status=knowledge_status,
                learned_at_scene_version_id=candidate.scene_version_id,
                confidence=candidate.confidence,
            )
        )
        return

    if candidate.candidate_type == "timeline_event":
        session.add(
            TimelineEvent(
                project_id=project_id,
                scene_version_id=candidate.scene_version_id,
                event_text=candidate.content_json.get("event_text", ""),
                timeline_order=timeline_order,
                affected_character_ids=candidate.content_json.get("affected_character_ids", []),
            )
        )
        return

    raise ValidationAppError(
        "unsupported memory candidate type",
        {"candidate_type": candidate.candidate_type},
    )


async def _scene_metadata(
    session: AsyncSession,
    scene_version_id: str,
) -> tuple[str, int]:
    result = await session.execute(
        select(Volume.project_id, Scene.timeline_order)
        .select_from(SceneVersion)
        .join(Scene, SceneVersion.scene_id == Scene.id)
        .join(Chapter, Scene.chapter_id == Chapter.id)
        .join(Volume, Chapter.volume_id == Volume.id)
        .where(SceneVersion.id == scene_version_id)
    )
    metadata = result.one_or_none()
    if metadata is None:
        raise NotFoundError(
            "scene version not found",
            {"version_id": scene_version_id},
        )
    return metadata.project_id, metadata.timeline_order
