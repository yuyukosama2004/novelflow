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
from app.services.text_chunks import TextChunk, split_text_chunks


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
        issues: dict[tuple[str, str, str], ReviewIssue] = {}
        for chunk in split_text_chunks(version.content_text):
            request = LLMRequest(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "You are a continuity editor for fiction. "
                            "Given a scene draft chunk and character/world constraints, "
                            "find all issues where the draft violates a constraint. "
                            "Output ONLY a JSON array of issues. "
                            "Each issue must have: issue_type, severity, evidence, "
                            "conflict_rule, suggestion, confidence. If no issues found, "
                            "output []. No other text."
                        ),
                    ),
                    LLMMessage(
                        role="user",
                        content=self.build_prompt(version, context, chunk),
                    ),
                ],
                max_tokens=1024,
                temperature=0.3,
            )
            items = await generate_json_array(
                self.llm,
                self.provider,
                request,
                ReviewItem,
            )
            for item in items:
                evidence = json.dumps(item.evidence, ensure_ascii=False)
                key = (item.issue_type, item.conflict_rule, evidence)
                issues.setdefault(
                    key,
                    ReviewIssue(
                        scene_version_id=version.id,
                        issue_type=item.issue_type,
                        severity=item.severity,
                        evidence_json=evidence,
                        conflict_rule=item.conflict_rule,
                        suggestion=item.suggestion,
                        confidence=item.confidence,
                        source_chunk_index=chunk.index,
                        source_start=chunk.start,
                        source_end=chunk.end,
                        status="open",
                    ),
                )
        return list(issues.values())

    def build_prompt(
        self,
        version: SceneVersion,
        context: SceneContext,
        chunk: TextChunk | None = None,
    ) -> str:
        active_chunk = chunk or split_text_chunks(version.content_text)[0]
        parts: list[str] = []
        parts.append(
            f"## Scene Draft Chunk {active_chunk.index + 1} "
            f"(characters {active_chunk.start}-{active_chunk.end})"
        )
        parts.append(active_chunk.text)
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
            parts.append(f"  Future locked facts: {json.dumps(ch.knowledge_future_locked)}")
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
