from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter

logger = logging.getLogger(__name__)


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
        plan_request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are a fiction writing planner. "
                        "Based on the scene card below, write a brief "
                        "scene plan (beats, key moments, emotional arc). "
                        "Output only the plan, no meta-commentary. "
                        "Keep it under 300 characters."
                    ),
                ),
                LLMMessage(role="user", content=self.user_prompt),
            ],
            model=self.state.model,
            max_tokens=512,
            temperature=0.7,
        )
        response = await self.llm.generate(plan_request, self.state.provider)
        return response.content

    async def _draft(self) -> AsyncIterator[dict]:
        full_prompt = (
            f"Planning result:\n{self.state.plan}\n\n"
            f"Now write the full scene based on the plan and "
            f"the scene card above.\n{self.user_prompt}"
        )
        draft_request = LLMRequest(
            messages=[
                LLMMessage(role="system", content=self.system_prompt),
                LLMMessage(role="user", content=full_prompt),
            ],
            model=self.state.model,
            max_tokens=4096,
            temperature=0.8,
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
