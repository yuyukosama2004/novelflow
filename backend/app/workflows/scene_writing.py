from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter

logger = logging.getLogger(__name__)


def perspective_warning(content: str, pov_type: str) -> str:
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


def build_plan_request(user_prompt: str, model: str) -> LLMRequest:
    return LLMRequest(
        messages=[
            LLMMessage(
                role="system",
                content=(
                    "你是中文小说场景策划。基于场景卡，用中文输出两行简短计划："
                    "第一行必须以“摘要：”开头，用 40—80 字概括本场发生了什么；"
                    "第二行必须以“节拍：”开头，列出关键动作、转折与情绪变化。"
                    "不要输出元评论，总长度不超过 300 字。"
                ),
            ),
            LLMMessage(role="user", content=user_prompt),
        ],
        model=model,
        max_tokens=512,
        temperature=0.7,
    )


def build_draft_request(
    system_prompt: str,
    user_prompt: str,
    plan: str,
    model: str,
    max_output_tokens: int,
) -> LLMRequest:
    full_prompt = (
        f"Planning result:\n{plan}\n\n"
        f"Now write the full scene based on the plan and "
        f"the scene card above.\n{user_prompt}"
    )
    return LLMRequest(
        messages=[
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=full_prompt),
        ],
        model=model,
        max_tokens=max_output_tokens,
        temperature=0.8,
    )


@dataclass
class WorkflowState:
    """State for the persisted scene-writing workflow."""

    messages: list[dict[str, str]] = field(default_factory=list)
    scene_id: str = ""
    scene_title: str = ""
    plan: str = ""
    draft: str = ""
    final_content: str = ""
    status: str = "planning"  # planning | drafting | waiting_review | done | cancelled | error
    error: str = ""
    provider: str = "deepseek"
    model: str = ""
    max_output_tokens: int = 4096
    prompt_snapshot: dict = field(default_factory=dict)
    context_manifest: dict = field(default_factory=dict)
    run_id: str = ""
    events: list[dict] = field(default_factory=list)


class SceneWritingWorkflow:
    """Explicit async state machine for scene planning and drafting.

    Uses simple async generator pattern for each node, emitting
    SSE-compatible events as the workflow progresses.
    """

    def __init__(
        self,
        state: WorkflowState,
        llm_router: LLMRouter,
        system_prompt: str,
        user_prompt: str,
        context_manifest: dict,
    ) -> None:
        self.state = state
        self.llm = llm_router
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.context_manifest = context_manifest

    async def run(self) -> AsyncIterator[dict]:
        """Execute the full workflow, yielding SSE events."""
        self.state.status = "planning"
        yield self._event("node_start", {"node": "planning"})

        try:
            # Node 1: Planning
            plan = await self._plan()
            self.state.plan = plan
            yield self._event("node_complete", {"node": "planning", "plan": plan})

            # Node 2: Drafting
            self.state.status = "drafting"
            yield self._event("node_start", {"node": "drafting"})

            async for chunk in self._draft():
                yield chunk

            self.state.status = "waiting_review"
            yield self._event(
                "node_complete",
                {"node": "drafting", "content": self.state.draft},
            )
            yield self._event("waiting_review", {"message": "Waiting for user approval"})

        except Exception as exc:
            self.state.status = "error"
            logger.exception("scene writing workflow failed", exc_info=exc)
            self.state.error = "生成任务执行失败"
            yield self._event("error", {"error": "生成失败，请稍后重试"})
            return

        yield self._event("workflow_complete", {"status": self.state.status})

    async def _plan(self) -> str:
        plan_request = build_plan_request(self.user_prompt, self.state.model)
        response = await self.llm.generate(plan_request, self.state.provider)
        return response.content

    async def _draft(self) -> AsyncIterator[dict]:
        draft_request = build_draft_request(
            self.system_prompt,
            self.user_prompt,
            self.state.plan,
            self.state.model,
            self.state.max_output_tokens,
        )
        async for chunk in self.llm.stream_generate(draft_request, self.state.provider):
            self.state.draft += chunk.content_delta
            yield self._event(
                "content_delta",
                {
                    "content_delta": chunk.content_delta,
                    "finish_reason": chunk.finish_reason,
                },
            )

    def _event(self, event_type: str, data: dict[str, Any]) -> dict:
        event = {
            "event_id": len(self.state.events) + 1,
            "run_id": self.state.run_id,
            "event": event_type,
            "status": self.state.status,
            **data,
        }
        self.state.events.append(event)
        return event
