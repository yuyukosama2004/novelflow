from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    MemoryExtractionError,
    NotFoundError,
    ValidationAppError,
)
from app.core.responses import success
from app.database.session import get_session
from app.llm.router import LLMRouter
from app.models.base import utc_now
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.memory import MemoryCandidate, MemoryExtractionRun, TimelineEvent
from app.schemas.memory import (
    MemoryCandidateOut,
    MemoryExtractionResultOut,
    MemoryExtractionRunOut,
    UpdateCandidateRequest,
)
from app.services.context_builder import ContextBuilder
from app.services.manuscript_service import ManuscriptService
from app.services.memory_curator import MemoryCurator

router = APIRouter()


def extraction_result(
    run: MemoryExtractionRun,
    candidates: list[MemoryCandidate],
) -> MemoryExtractionResultOut:
    return MemoryExtractionResultOut(
        run=MemoryExtractionRunOut.model_validate(run),
        candidates=[MemoryCandidateOut.model_validate(candidate) for candidate in candidates],
    )


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

    run = MemoryExtractionRun(
        scene_version_id=version.id,
        model_profile_id=version.model_profile_id,
        status="pending",
        prompt_snapshot_json={},
    )
    session.add(run)
    await session.commit()
    run_id = run.id

    try:
        run.status = "running"
        run.started_at = utc_now()
        await session.commit()

        builder = ContextBuilder(session)
        ctx = await builder.build_for_scene(version.scene_id)
        curator = MemoryCurator(LLMRouter(), settings.default_model_provider)
        run.prompt_snapshot_json = {
            "provider": settings.default_model_provider,
            "prompt": curator.build_prompt(version, ctx),
        }
        candidates = await curator.extract(version, ctx)

        for candidate in candidates:
            candidate.extraction_run_id = run.id
            candidate.status = "pending"
            session.add(candidate)
        run.status = "completed"
        run.completed_at = utc_now()
        await session.commit()
    except Exception:
        await session.rollback()
        failed_run = await session.get(MemoryExtractionRun, run_id)
        if failed_run is not None:
            failed_run.status = "failed"
            failed_run.completed_at = utc_now()
        await session.commit()
        raise MemoryExtractionError(
            "memory extraction failed",
            {"memory_extraction_run_id": run_id},
        ) from None

    return success(extraction_result(run, candidates), request)


@router.get("/scene-versions/{version_id}/memory-extraction-runs")
async def list_memory_extraction_runs(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ManuscriptService(session).get_version(version_id)
    result = await session.execute(
        select(MemoryExtractionRun)
        .where(MemoryExtractionRun.scene_version_id == version_id)
        .order_by(MemoryExtractionRun.created_at.desc(), MemoryExtractionRun.id.desc())
    )
    return success(
        [MemoryExtractionRunOut.model_validate(run) for run in result.scalars().all()],
        request,
    )


@router.get("/scene-versions/{version_id}/candidates")
async def list_candidates(
    version_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List all candidates for a version so no older pending item is hidden."""
    await ManuscriptService(session).get_version(version_id)
    result = await session.execute(
        select(MemoryCandidate)
        .where(MemoryCandidate.scene_version_id == version_id)
        .order_by(
            MemoryCandidate.created_at.desc(),
            MemoryCandidate.confidence.desc(),
        )
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
        await _ensure_candidate_source_is_approved(session, candidate)
        await _apply_candidate(session, candidate)

    candidate.status = payload.status
    await session.commit()
    return success(MemoryCandidateOut.model_validate(candidate), request)


async def _ensure_candidate_source_is_approved(
    session: AsyncSession,
    candidate: MemoryCandidate,
) -> None:
    result = await session.execute(
        select(Scene.approved_version_id)
        .select_from(SceneVersion)
        .join(Scene, SceneVersion.scene_id == Scene.id)
        .where(SceneVersion.id == candidate.scene_version_id)
    )
    approved_version_id = result.scalar_one_or_none()
    if approved_version_id != candidate.scene_version_id:
        raise ConflictError(
            "memory candidate source is not the approved version",
            {
                "reason": "CANDIDATE_SOURCE_NOT_APPROVED",
                "scene_version_id": candidate.scene_version_id,
            },
        )


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
