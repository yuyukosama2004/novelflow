"""AI-assisted planning for the intentionally lightweight quick-creation entry."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.responses import success
from app.database.session import get_session
from app.llm.base import LLMMessage, LLMRequest
from app.services.model_runtime import ModelRuntimeResolver
from app.services.structured_output import generate_json_array

router = APIRouter()


class QuickSceneCard(BaseModel):
    title: str = "开篇场景"
    goal: str = "让主角面对核心问题。"
    conflict: str = "主角的目标受到阻碍。"
    turning_point: str = "出现迫使主角选择的新信息。"
    ending_hook: str = "留下推动下一步行动的悬念。"


class QuickCreationPlan(BaseModel):
    title_candidates: list[str] = Field(default_factory=list)
    summary: str = ""
    protagonist: str = "主角"
    genre: str = ""
    tone: str = ""
    scene: QuickSceneCard = Field(default_factory=QuickSceneCard)


class QuickCreationPlanRequest(BaseModel):
    idea: str = Field(min_length=4, max_length=4000)
    target_length: str = Field(default="3000 字短篇", max_length=80)
    draft_kind: str = Field(default="short", max_length=20)
    model_profile_id: str | None = None


def _fallback_plan(payload: QuickCreationPlanRequest) -> QuickCreationPlan:
    compact = re.sub(r"\s+", "", payload.idea).strip()
    return QuickCreationPlan(
        title_candidates=["未命名故事"],
        summary=compact[:160],
        protagonist="待命名主角",
        tone="紧凑、有画面感",
        scene=QuickSceneCard(
            title="开篇场景" if payload.draft_kind == "opening" else "短篇开场",
            goal="让主角直面这个点子中最关键的麻烦。",
            conflict=compact[:200],
            turning_point="出现改变主角判断的新信息。",
            ending_hook="以一个必须立刻回应的问题收束本场。",
        ),
    )


@router.post("/quick-creation/plan")
async def plan_quick_creation(
    payload: QuickCreationPlanRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Turn a rough idea into editable, non-canonical setup candidates."""
    system = (
        "你是中文小说编辑。把作者的粗略点子整理成可编辑的快速创作候选，"
        "不要创作正文，不要把任何内容当作正式设定。"
        "只输出 JSON 数组，且数组只有一个对象。对象字段："
        "title_candidates（3 个与内容相关、简洁的中文书名），summary（80—160 字简介），"
        "protagonist，genre，tone，scene。scene 必含 title、goal、conflict、turning_point、ending_hook。"
        "场景卡要是可执行的正规描述，不能直接照抄作者原话。"
    )
    try:
        runtime = await ModelRuntimeResolver(session).resolve_default(
            payload.model_profile_id
        )
        items = await generate_json_array(
            runtime.router,
            runtime.provider,
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content=system),
                    LLMMessage(
                        role="user",
                        content=(
                            f"点子：{payload.idea}\n目标篇幅：{payload.target_length}\n"
                            f"创作形式：{'开篇试写' if payload.draft_kind == 'opening' else '完整短篇'}"
                        ),
                    ),
                ],
                model=runtime.model,
                max_tokens=1200,
                temperature=0.7,
            ),
            QuickCreationPlan,
        )
        plan = items[0] if items else _fallback_plan(payload)
    except Exception:
        # Quick creation remains usable when a model is not available. The user
        # can still edit every fallback field before anything is persisted.
        plan = _fallback_plan(payload)

    titles = [title.strip() for title in plan.title_candidates if title.strip()]
    plan.title_candidates = (titles + _fallback_plan(payload).title_candidates)[:3]
    return success(plan, request)
