from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter
from app.models.manuscript import SceneVersion
from app.models.review import ReviewIssue
from app.services.context_builder import SceneContext
from app.services.structured_output import generate_json_array


class ReviewItem(BaseModel):
    issue_type: str
    severity: Literal["low", "medium", "high", "blocking"]
    evidence: Any
    conflict_rule: str
    suggestion: str
    confidence: float = Field(ge=0.0, le=1.0)


class ContinuityReviewer:
    """Checks scene content against character/world constraints."""

    def __init__(self, llm: LLMRouter, provider: str = "deepseek") -> None:
        self.llm = llm
        self.provider = provider

    async def review(
        self,
        version: SceneVersion,
        context: SceneContext,
    ) -> list[ReviewIssue]:
        """Run continuity review on a scene version."""
        prompt = self._build_review_prompt(version, context)

        request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are a continuity editor for fiction. "
                        "Given a scene draft and character/world constraints, "
                        "find all issues where the draft violates a constraint. "
                        "Output ONLY a JSON array of issues. "
                        "Each issue must have: issue_type, severity, "
                        "evidence, conflict_rule, suggestion, confidence. "
                        "If no issues found, output []. No other text."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            max_tokens=1024,
            temperature=0.3,
        )

        issues_data = await generate_json_array(
            self.llm,
            self.provider,
            request,
            ReviewItem,
        )

        return [
            ReviewIssue(
                scene_version_id=version.id,
                issue_type=item.issue_type,
                severity=item.severity,
                evidence_json=json.dumps(item.evidence, ensure_ascii=False),
                conflict_rule=item.conflict_rule,
                suggestion=item.suggestion,
                confidence=item.confidence,
                status="open",
            )
            for item in issues_data
        ]

    def _build_review_prompt(
        self,
        version: SceneVersion,
        context: SceneContext,
    ) -> str:
        parts: list[str] = []
        parts.append("## Scene Draft")
        parts.append(version.content_markdown[:3000])
        parts.append("")

        if context.previous_scene:
            parts.append("## Previous Scene")
            parts.append(context.previous_scene.content_preview)
            parts.append("")

        parts.append("## Character Constraints")
        for ch in context.characters:
            parts.append(f"\n- {ch.name}:")
            parts.append(f"  Forbidden: {json.dumps(ch.forbidden_behaviors)}")
            parts.append(f"  Must NOT know: {json.dumps(ch.knowledge_unknown)}")
            parts.append(f"  Known: {json.dumps(ch.knowledge_known)}")
            if ch.current_state:
                parts.append(f"  State: {json.dumps(ch.current_state)}")

        if context.world_facts:
            parts.append("\n## World Facts")
            for wf in context.world_facts:
                parts.append(f"- {wf.name}: {wf.summary}")

        parts.append("")
        parts.append("## Scene Card Constraints")
        parts.append("Must include: " + json.dumps(context.current_scene.must_include_json))
        parts.append("Must NOT reveal: " + json.dumps(context.current_scene.must_not_reveal_json))
        parts.append("Forbidden actions: " + json.dumps(context.current_scene.forbidden_actions_json))

        parts.append("")
        parts.append(
            "Review the scene draft against ALL constraints above. "
            "Output a JSON array of issues found. "
            "Use types: knowledge_boundary, character_consistency, "
            "injury_fact, timeline, deprecated_world, forbidden_action, "
            "must_not_reveal, missing_must_include. "
            "Severity: low, medium, high, blocking."
        )
        return "\n".join(parts)
