from __future__ import annotations

import json

from pydantic import BaseModel, Field

from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter
from app.models.manuscript import SceneVersion
from app.models.memory import MemoryCandidate
from app.services.context_builder import SceneContext
from app.services.structured_output import generate_json_array


class MemoryItem(BaseModel):
    candidate_type: str
    target_entity_type: str
    target_entity_id: str | None = None
    content_json: dict
    evidence: str
    confidence: float = Field(ge=0.0, le=1.0)


class MemoryCurator:
    """Extracts state changes from approved scene content as candidates."""

    def __init__(self, llm: LLMRouter, provider: str = "deepseek") -> None:
        self.llm = llm
        self.provider = provider

    async def extract(
        self,
        version: SceneVersion,
        context: SceneContext,
    ) -> list[MemoryCandidate]:
        """Extract memory candidates from an approved version."""
        prompt = self.build_prompt(version, context)

        request = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You extract story state changes from fiction. "
                        "Given a scene and character context, identify "
                        "what changed: injuries, knowledge gained, "
                        "emotional shifts, relationship changes, "
                        "timeline events. "
                        "Output ONLY a JSON array. Each item: "
                        "candidate_type, target_entity_type, "
                        "target_entity_id (or null), content_json, "
                        "evidence (quote from text), confidence."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
            max_tokens=1024,
            temperature=0.3,
        )

        items = await generate_json_array(
            self.llm,
            self.provider,
            request,
            MemoryItem,
        )

        return [
            MemoryCandidate(
                scene_version_id=version.id,
                candidate_type=item.candidate_type,
                target_entity_type=item.target_entity_type,
                target_entity_id=item.target_entity_id,
                content_json=item.content_json,
                evidence=item.evidence,
                confidence=item.confidence,
                status="pending",
            )
            for item in items
        ]

    def build_prompt(
        self,
        version: SceneVersion,
        context: SceneContext,
    ) -> str:
        parts: list[str] = []
        parts.append("## Scene Content")
        parts.append(version.content_markdown[:3000])
        parts.append("")

        parts.append("## Characters Before This Scene")
        for ch in context.characters:
            parts.append(f"- {ch.name} ({ch.role})")
            if ch.current_state:
                parts.append(f"  Previous state: {json.dumps(ch.current_state)}")
            parts.append(f"  Known: {json.dumps(ch.knowledge_known)}")
            parts.append(f"  Unknown: {json.dumps(ch.knowledge_unknown)}")

        parts.append("")
        parts.append(
            "Extract all state changes from this scene. Types: "
            "character_state (injury/emotion/goal change), "
            "character_knowledge (learned secret), "
            "timeline_event, relationship_change, world_fact_update."
        )
        return "\n".join(parts)
