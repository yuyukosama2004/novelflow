from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.database.session import get_session
from app.llm.router import LLMRouter
from app.models.workflow import WorkflowRun
from app.schemas.manuscript import SceneVersionCreate, SceneVersionRead
from app.services.context_builder import ContextBuilder
from app.services.manuscript_service import ManuscriptService
from app.services.model_runtime import ModelRuntimeResolver
from app.workflows.scene_writing import SceneWritingWorkflow, WorkflowState

router = APIRouter()
logger = logging.getLogger(__name__)


def _summary(content: str, max_len: int = 200) -> str:
    return content[:max_len] + "..." if len(content) > max_len else content


def _build_system_prompt() -> str:
    return (
        "You are a fiction writer. Write in Chinese. "
        "Write the scene content based on the scene card and context "
        "provided below. Follow all constraints. "
        "Output only the scene narrative text, no meta-commentary."
    )


def _build_user_prompt(ctx, scene) -> str:  # type: ignore[no-untyped-def]
    parts: list[str] = []

    parts.append("## Scene Card")
    parts.append(f"Title: {scene.title}")
    parts.append(f"POV: {scene.pov_character_id or 'third-person'}")
    parts.append(f"Time: {scene.time_text or 'not specified'}")
    parts.append(f"Goal: {scene.goal or 'not specified'}")
    parts.append(f"Conflict: {scene.conflict or 'not specified'}")
    parts.append(f"Turning Point: {scene.turning_point or 'not specified'}")

    if scene.must_include_json:
        parts.append("Must Include: " + json.dumps(scene.must_include_json, ensure_ascii=False))
    if scene.must_not_reveal_json:
        parts.append("Must NOT Reveal: " + json.dumps(scene.must_not_reveal_json, ensure_ascii=False))
    if scene.forbidden_actions_json:
        parts.append("Forbidden Actions: " + json.dumps(scene.forbidden_actions_json, ensure_ascii=False))

    if ctx.previous_scene:
        parts.append("")
        parts.append(f"## Previous Scene ({ctx.previous_scene.title})")
        parts.append(ctx.previous_scene.content_preview)

    if ctx.characters:
        parts.append("")
        parts.append("## Characters")
        for ch in ctx.characters:
            parts.append(f"\n- {ch.name} ({ch.role}):")
            parts.append(f"  Identity: {ch.public_identity or 'n/a'}")
            parts.append(f"  Speech: {ch.speech_style or 'n/a'}")
            parts.append(f"  Decision: {ch.decision_pattern or 'n/a'}")
            parts.append(f"  Wants: {ch.core_desire or 'n/a'}")
            parts.append(f"  Fears: {ch.core_fear or 'n/a'}")
            parts.append("  Forbidden: " + json.dumps(ch.forbidden_behaviors or [], ensure_ascii=False))
            parts.append("  Known facts: " + json.dumps(ch.knowledge_known or [], ensure_ascii=False))
            parts.append("  Must NOT know: " + json.dumps(ch.knowledge_unknown or [], ensure_ascii=False))
            if ch.current_state:
                parts.append("  Current state: " + json.dumps(ch.current_state, ensure_ascii=False))

    if ctx.world_facts:
        parts.append("")
        parts.append("## World Facts (hard constraints)")
        for wf in ctx.world_facts:
            parts.append(f"- [{wf.entry_type}] {wf.name}: {wf.summary}")
            if wf.content:
                parts.append(f"  {wf.content[:200]}")

    parts.append("")
    parts.append("Write the scene narrative now.")
    return "\n".join(parts)


class WorkflowRunOut(BaseModel):
    id: str
    model_profile_id: str | None
    provider: str
    model: str
    run_type: str
    status: str
    plan: str
    draft: str
    final_content: str
    error: str
    version_created_id: str | None

    model_config = {"from_attributes": True}


class GenerateSceneRequest(BaseModel):
    model_profile_id: str | None = None


@router.get("/workflows/runs/{run_id}")
async def get_workflow_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Query a workflow run by ID."""
    from app.core.responses import success

    run = await session.get(WorkflowRun, run_id)
    if run is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("workflow run not found", {"run_id": run_id})
    return success(WorkflowRunOut.model_validate(run), request)


@router.post("/scenes/{scene_id}/generate")
async def generate_scene_stream(
    scene_id: str,
    request: Request,
    payload: GenerateSceneRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Stream-generate scene content via the persisted workflow state machine."""
    manuscript = ManuscriptService(session)
    scene = await manuscript.get_scene(scene_id)
    runtime = await ModelRuntimeResolver(session).resolve_for_scene(
        scene_id,
        payload.model_profile_id if payload else None,
    )

    # 并发锁：检查是否有正在运行中的生成任务
    active_run = await session.execute(
        select(WorkflowRun)
        .where(
            WorkflowRun.scene_id == scene_id,
            WorkflowRun.status.in_(["pending", "planning", "drafting"]),
        )
        .limit(1)
    )
    if active_run.scalar_one_or_none() is not None:
        raise ConflictError(
            "此场景已有正在进行的生成任务，请等待完成或取消后再试",
            {"scene_id": scene_id},
        )

    builder = ContextBuilder(session)
    ctx = await builder.build_for_scene(scene_id)

    run_id = getattr(request.state, "request_id", f"run_{scene_id[:8]}")
    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(ctx, scene)
    provider = runtime.provider

    # Persist workflow run
    wf_run = WorkflowRun(
        id=run_id,
        scene_id=scene_id,
        model_profile_id=runtime.profile_id,
        run_type="scene_writing",
        status="pending",
        provider=provider,
        model=runtime.model,
        prompt_snapshot_json={
            "system": system_prompt,
            "user": user_prompt,
        },
        context_manifest_json=ctx.manifest,
    )
    session.add(wf_run)
    await session.commit()

    state = WorkflowState(
        scene_id=scene_id,
        scene_title=scene.title,
        provider=provider,
        model=runtime.model,
        run_id=run_id,
        prompt_snapshot={"system": system_prompt, "user": user_prompt},
        context_manifest=ctx.manifest,
    )
    llm = runtime.router if runtime.profile_id else LLMRouter()
    workflow = SceneWritingWorkflow(state, llm, system_prompt, user_prompt, ctx.manifest)

    async def stream():  # type: ignore[no-untyped-def]
        try:
            async for event in workflow.run():
                # Update persisted run
                wf_run.status = state.status
                wf_run.plan = state.plan
                wf_run.draft = state.draft
                wf_run.model = state.model
                wf_run.events_json = state.events
                wf_run.error = state.error
                await session.commit()

                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # A successful generation remains a draft awaiting explicit approval.
            if state.status == "waiting_review" and state.draft.strip():
                version_payload = SceneVersionCreate(
                    content_json={
                        "type": "doc",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": state.draft}],
                            }
                        ],
                    },
                    content_markdown=state.draft,
                    summary=_summary(state.draft),
                    source_type="ai_generated",
                    model_profile_id=runtime.profile_id,
                    prompt_snapshot_json=state.prompt_snapshot,
                    context_manifest_json=state.context_manifest,
                )
                version = await manuscript.create_version(scene_id, version_payload)
                wf_run.version_created_id = version.id
                wf_run.final_content = state.draft
                wf_run.status = "waiting_review"
                await session.commit()

                done_data = {
                    "run_id": run_id,
                    "event": "version_created",
                    "status": "waiting_review",
                    "version": SceneVersionRead.model_validate(version).model_dump(mode="json"),
                }
                yield ("data: " + json.dumps(done_data, ensure_ascii=False) + "\n\n")
        except asyncio.CancelledError:
            wf_run.status = "cancelled"
            wf_run.error = "client cancelled generation"
            await session.commit()
            raise
        except Exception as exc:
            wf_run.status = "error"
            wf_run.error = str(exc)
            await session.commit()
            error_data = {"run_id": run_id, "event": "error", "error": str(exc)}
            yield ("data: " + json.dumps(error_data, ensure_ascii=False) + "\n\n")
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Run-Id": run_id,
        },
    )
