from __future__ import annotations

import asyncio
import json
import logging
import re
from math import ceil
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.responses import success
from app.database.session import get_session
from app.llm.router import LLMRouter
from app.models.manuscript import Chapter, Scene, Volume
from app.models.project import NovelProject
from app.models.workflow import WorkflowRun
from app.schemas.manuscript import SceneVersionCreate, SceneVersionRead
from app.services.context_builder import ContextBuilder, SceneContext
from app.services.manuscript_service import ManuscriptService
from app.services.model_runtime import ModelRuntimeResolver
from app.services.writing_style import perspective_instruction, writing_style_instruction
from app.workflows.scene_writing import SceneWritingWorkflow, WorkflowState

router = APIRouter()
logger = logging.getLogger(__name__)


def _summary_from_plan(plan: str, scene_title: str, generation_mode: str) -> str:
    """Return a navigable version label without leaking raw manuscript text."""
    match = re.search(r"(?:摘要|概述)\s*[：:]\s*([^\n]+)", plan)
    if match:
        summary = match.group(1).strip().strip("。")
        if summary:
            return summary[:120]
    mode_label = {"new": "AI 初稿", "rewrite": "AI 重写", "polish": "AI 润色"}[
        generation_mode
    ]
    return f"{scene_title} · {mode_label}，待作者审核"


def _perspective_warning(content: str, pov_type: str) -> str:
    """Detect only clear, high-signal perspective misses; dialogue is ignored."""
    if len(content.strip()) < 300:
        return ""
    narrative = re.sub(r"“[^”]*”|「[^」]*」|\"[^\"]*\"", "", content)
    first_person_markers = len(re.findall(r"我(?=[一-龥，。！？；：])", narrative))
    if pov_type.startswith("third_person") and first_person_markers >= 5:
        return "检测到较多第一人称叙述痕迹；请在审阅时确认重写是否已转换为全书设定的第三人称。"
    if pov_type == "first_person" and first_person_markers == 0:
        return "未检测到明确第一人称叙述；请在审阅时确认是否符合全书设定的第一人称。"
    return ""


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
    events_json: list[dict]

    model_config = {"from_attributes": True}


class GenerateSceneRequest(BaseModel):
    model_profile_id: str | None = None
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
    run = await session.get(WorkflowRun, run_id)
    if run is None:
        raise NotFoundError("workflow run not found", {"run_id": run_id})
    if run.status in {"pending", "planning", "drafting"}:
        run.status = "cancelled"
        run.error = "用户已取消生成"
        await session.commit()
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
    project = await _project_for_scene(session, scene_id)
    generation = payload or GenerateSceneRequest()
    runtime = await ModelRuntimeResolver(session).resolve_for_scene(
        scene_id,
        generation.model_profile_id,
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
            "generation_mode": generation.generation_mode,
            "target_word_count": target_word_count,
        },
        context_manifest_json=ctx.manifest,
    )
    session.add(wf_run)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise ConflictError(
            "此场景已有正在进行的生成任务，请等待完成或取消后再试",
            {"reason": "ACTIVE_WORKFLOW_EXISTS", "scene_id": scene_id},
        ) from None

    state = WorkflowState(
        scene_id=scene_id,
        scene_title=scene.title,
        provider=provider,
        model=runtime.model,
        max_output_tokens=max_output_tokens,
        run_id=run_id,
        prompt_snapshot={
            "system": system_prompt,
            "user": user_prompt,
            "generation_mode": generation.generation_mode,
            "target_word_count": target_word_count,
        },
        context_manifest=ctx.manifest,
    )
    llm = runtime.router if runtime.profile_id else LLMRouter()
    workflow = SceneWritingWorkflow(state, llm, system_prompt, user_prompt, ctx.manifest)

    async def stream():  # type: ignore[no-untyped-def]
        try:
            async for event in workflow.run():
                await session.refresh(wf_run)
                if wf_run.status == "cancelled":
                    state.status = "cancelled"
                    break
                # Update persisted run
                wf_run.status = state.status
                wf_run.plan = state.plan
                wf_run.draft = state.draft
                wf_run.model = state.model
                wf_run.events_json = state.events
                wf_run.error = state.error
                await session.commit()

                yield (f"id: {event['event_id']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n")

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
                    summary=_summary_from_plan(
                        state.plan,
                        scene.title,
                        generation.generation_mode,
                    ),
                    source_type=("ai_generated" if generation.generation_mode == "new" else "ai_revised"),
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
                    "event_id": len(state.events) + 1,
                    "run_id": run_id,
                    "event": "version_created",
                    "status": "waiting_review",
                    "version": SceneVersionRead.model_validate(version).model_dump(mode="json"),
                }
                perspective_warning = _perspective_warning(state.draft, project.pov_type)
                if perspective_warning:
                    done_data["perspective_warning"] = perspective_warning
                state.events.append(done_data)
                wf_run.events_json = state.events
                await session.commit()
                yield (
                    f"id: {done_data['event_id']}\n"
                    "data: " + json.dumps(done_data, ensure_ascii=False) + "\n\n"
                )
        except asyncio.CancelledError:
            wf_run.status = "cancelled"
            wf_run.error = "client cancelled generation"
            await session.commit()
            raise
        except Exception:
            wf_run.status = "error"
            wf_run.error = "生成任务执行失败"
            await session.commit()
            error_data = {
                "event_id": len(state.events) + 1,
                "run_id": run_id,
                "event": "error",
                "error": "生成失败，请稍后重试",
            }
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
