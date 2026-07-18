from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from math import ceil
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import ConflictError, NotFoundError
from app.core.responses import success
from app.database.session import get_session
from app.models.manuscript import Chapter, Scene, Volume
from app.models.project import NovelProject
from app.models.workflow import WorkflowEvent, WorkflowRun
from app.services.context_builder import ContextBuilder, SceneContext
from app.services.manuscript_service import ManuscriptService
from app.services.model_runtime import ModelRuntimeResolver
from app.services.writing_style import perspective_instruction, writing_style_instruction
from app.workflows.runtime import TERMINAL_RUN_STATUSES, WorkflowRuntime, stable_json_hash
from app.workflows.scene_writing import perspective_warning

router = APIRouter()


def _perspective_warning(content: str, pov_type: str) -> str:
    return perspective_warning(content, pov_type)


def _build_system_prompt(
    project: NovelProject,
    target_word_count: int,
    generation_mode: str,
    instruction: str,
) -> str:
    mode_instruction = {
        "new": "从场景卡和上下文创作一篇全新正文。",
        "rewrite": "根据原稿和作者要求重写完整场景；保留未被作者要求改变的既有事实。",
        "polish": "润色原稿的语言、节奏和表达；除非作者明确要求，否则不得改变事件、人物关系或信息量。",
    }[generation_mode]
    parts = [
        "你是中文小说作者。只输出完整场景正文，不输出标题、说明、写作计划或元评论。",
        "约束优先级（从高到低）：既有正史、人物知识与禁止事项；全书写作设置；场景卡；本次作者要求；原稿措辞。"
        "本次作者要求只能调整本场的节奏、侧重点和表达，不得覆盖全书设定的人称或文风。",
        perspective_instruction(project.pov_type),
        writing_style_instruction(
            project.writing_style_preset,
            project.writing_style_custom,
        ),
        f"目标长度：约 {target_word_count} 个汉字，允许上下浮动约 15%。",
        mode_instruction,
    ]
    if generation_mode == "rewrite":
        if project.pov_type == "first_person":
            parts.append(
                "这是硬约束：重写时必须使用第一人称叙述。若原稿不是第一人称，应先转换叙述视角；对话内容可按人物自然保留。"
            )
        else:
            parts.append(
                "这是硬约束：重写时必须使用第三人称叙述。原稿若以“我”叙述，必须先转换为相应的第三人称叙述；"
                "仅人物对话中允许出现第一人称。不要把原稿的人称原样沿用。"
            )
    if instruction.strip():
        parts.append(f"本次作者要求（不得覆盖全书人称、文风或故事硬约束）：{instruction.strip()}")
    return "\n\n".join(parts)


def _build_user_prompt(
    ctx: SceneContext,
    scene: Scene,
    generation_mode: str,
    base_content: str,
) -> str:
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
            parts.append(
                "  Future locked (do not reveal): "
                + json.dumps(ch.knowledge_future_locked or [], ensure_ascii=False)
            )
            if ch.current_state:
                parts.append("  Current state: " + json.dumps(ch.current_state, ensure_ascii=False))

    if ctx.world_facts:
        parts.append("")
        parts.append("## World Facts (hard constraints)")
        for wf in ctx.world_facts:
            parts.append(f"- [{wf.entry_type}] {wf.name}: {wf.summary}")
            if wf.content:
                parts.append(f"  {wf.content[:200]}")

    if generation_mode in {"rewrite", "polish"}:
        parts.append("")
        parts.append("## 原稿")
        parts.append(base_content.strip() or "（原稿为空，请按场景卡创作完整正文）")

    parts.append("")
    parts.append("Write the scene narrative now.")
    return "\n".join(parts)


class WorkflowRunOut(BaseModel):
    id: str
    scene_id: str
    model_profile_id: str | None
    provider: str
    model: str
    run_type: str
    status: str
    attempt: int
    last_event_sequence: int
    current_step_key: str
    last_healthy_step_key: str
    blocked_reason: str
    plan: str
    draft: str
    final_content: str
    error: str
    version_created_id: str | None
    events_json: list[dict]

    model_config = {"from_attributes": True}


class GenerateSceneRequest(BaseModel):
    model_profile_id: str | None = None
    idempotency_key: str = Field(default="", max_length=128)
    generation_mode: Literal["new", "rewrite", "polish"] = "new"
    instruction: str = Field(default="", max_length=2000)
    base_content: str = Field(default="", max_length=50000)
    target_word_count: int | None = Field(default=None, ge=300, le=10000)


async def _project_for_scene(session: AsyncSession, scene_id: str) -> NovelProject:
    result = await session.execute(
        select(NovelProject)
        .join(Volume, Volume.project_id == NovelProject.id)
        .join(Chapter, Chapter.volume_id == Volume.id)
        .join(Scene, Scene.chapter_id == Chapter.id)
        .where(Scene.id == scene_id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError("project not found for scene", {"scene_id": scene_id})
    return project


@router.get("/workflows/runs/{run_id}")
async def get_workflow_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Query a workflow run by ID."""
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError("workflow run not found", {"run_id": run_id})
    return success(WorkflowRunOut.model_validate(run), request)


@router.get("/scenes/{scene_id}/workflow-runs")
async def list_scene_workflow_runs(
    scene_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    await ManuscriptService(session).get_scene(scene_id)
    result = await session.execute(
        select(WorkflowRun).where(WorkflowRun.scene_id == scene_id).order_by(WorkflowRun.created_at.desc())
    )
    return success(
        [WorkflowRunOut.model_validate(run) for run in result.scalars().all()],
        request,
    )


@router.post("/workflows/runs/{run_id}/cancel")
async def cancel_workflow_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    run = await WorkflowRuntime(session).request_cancel(run_id)
    if run is None:
        raise NotFoundError("workflow run not found", {"run_id": run_id})
    worker = getattr(request.app.state, "workflow_worker", None)
    if worker is not None:
        worker.cancel(run_id)
    return success(WorkflowRunOut.model_validate(run), request)


async def _stream_workflow_events(
    session_factory: async_sessionmaker[AsyncSession],
    run_id: str,
    after: int,
) -> AsyncIterator[str]:
    cursor = after
    loop = asyncio.get_running_loop()
    last_emit = loop.time()
    while True:
        async with session_factory() as session:
            events = (
                (
                    await session.execute(
                        select(WorkflowEvent)
                        .where(
                            WorkflowEvent.workflow_run_id == run_id,
                            WorkflowEvent.sequence_no > cursor,
                        )
                        .order_by(WorkflowEvent.sequence_no)
                    )
                )
                .scalars()
                .all()
            )
            run = await session.get(WorkflowRun, run_id)
        if run is None:
            return
        for event in events:
            cursor = event.sequence_no
            data = {
                "event_id": event.sequence_no,
                "run_id": run_id,
                "event": event.event_type,
                **event.payload_json,
            }
            yield f"id: {event.sequence_no}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            last_emit = loop.time()
        if run.status in TERMINAL_RUN_STATUSES and cursor < run.last_event_sequence:
            await asyncio.sleep(0)
            continue
        if run.status in TERMINAL_RUN_STATUSES:
            yield "data: [DONE]\n\n"
            return
        if loop.time() - last_emit >= 15:
            yield ": heartbeat\n\n"
            last_emit = loop.time()
        await asyncio.sleep(0.2)


@router.get("/workflows/runs/{run_id}/events")
async def resume_workflow_events(
    run_id: str,
    request: Request,
    after: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    if await session.get(WorkflowRun, run_id) is None:
        raise NotFoundError("workflow run not found", {"run_id": run_id})
    last_event_id = request.headers.get("last-event-id", "").strip()
    if last_event_id.isdigit():
        after = max(after, int(last_event_id))
    session_factory = request.app.state.workflow_session_factory
    return StreamingResponse(
        _stream_workflow_events(session_factory, run_id, after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Run-Id": run_id,
        },
    )


@router.post("/scenes/{scene_id}/generate")
async def generate_scene_stream(
    scene_id: str,
    request: Request,
    payload: GenerateSceneRequest | None = None,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Enqueue durable scene generation and stream its persisted event log."""
    manuscript = ManuscriptService(session)
    scene = await manuscript.get_scene(scene_id)
    project = await _project_for_scene(session, scene_id)
    generation = payload or GenerateSceneRequest()
    runtime = await ModelRuntimeResolver(session).resolve_for_scene(
        scene_id,
        generation.model_profile_id,
    )

    builder = ContextBuilder(session)
    ctx = await builder.build_for_scene(scene_id)

    target_word_count = generation.target_word_count or project.default_scene_word_count
    system_prompt = _build_system_prompt(
        project,
        target_word_count,
        generation.generation_mode,
        generation.instruction,
    )
    user_prompt = _build_user_prompt(
        ctx,
        scene,
        generation.generation_mode,
        generation.base_content,
    )
    max_output_tokens = min(8192, max(1024, ceil(target_word_count * 1.4)))
    provider = runtime.provider
    prompt_snapshot = {
        "system": system_prompt,
        "user": user_prompt,
        "generation_mode": generation.generation_mode,
        "target_word_count": target_word_count,
        "max_output_tokens": max_output_tokens,
        "pov_type": project.pov_type,
    }
    input_payload = {
        "run_type": "scene_writing",
        "scene_id": scene_id,
        "model_profile_id": runtime.profile_id,
        "provider": provider,
        "model": runtime.model,
        "prompt_snapshot": prompt_snapshot,
        "context_manifest": ctx.manifest,
    }
    idempotency_key = stable_json_hash(
        {
            "client_key": generation.idempotency_key,
            "run_type": "scene_writing",
            "scene_id": scene_id,
        }
        if generation.idempotency_key
        else input_payload
    )
    try:
        wf_run, _ = await WorkflowRuntime(session).enqueue(
            scene_id=scene_id,
            run_type="scene_writing",
            idempotency_key=idempotency_key,
            input_payload=input_payload,
            model_profile_id=runtime.profile_id,
            provider=provider,
            model=runtime.model,
            prompt_snapshot=prompt_snapshot,
            context_manifest=ctx.manifest,
        )
    except IntegrityError:
        raise ConflictError(
            "此场景已有正在进行的生成任务，请等待完成或取消后再试",
            {"reason": "ACTIVE_WORKFLOW_EXISTS", "scene_id": scene_id},
        ) from None
    worker = getattr(request.app.state, "workflow_worker", None)
    if worker is not None:
        worker.wake()
    session_factory = request.app.state.workflow_session_factory
    return StreamingResponse(
        _stream_workflow_events(session_factory, wf_run.id, 0),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Run-Id": wf_run.id,
        },
    )
