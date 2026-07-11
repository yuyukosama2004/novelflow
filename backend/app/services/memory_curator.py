from __future__ import annotations

import json

from app.llm.base import LLMMessage, LLMRequest
from app.llm.router import LLMRouter
from app.models.manuscript import SceneVersion
from app.models.memory import MemoryCandidate
from app.schemas.memory import MemoryItem
from app.services.context_builder import SceneContext
from app.services.structured_output import generate_json_array


class MemoryCurator:
    """Extracts state changes from scene content as pending candidates."""

    def __init__(self, llm: LLMRouter, provider: str = "deepseek") -> None:
        self.llm = llm
        self.provider = provider

    async def extract(
        self,
        version: SceneVersion,
        context: SceneContext,
    ) -> list[MemoryCandidate]:
        """Extract memory candidates from a scene version."""
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
                        "evidence (quote from text), confidence. "
                        "Use only the IDs supplied in the context."
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
                candidate_type=item.root.candidate_type,
                target_entity_type=item.root.target_entity_type,
                target_entity_id=item.root.target_entity_id,
                content_json=item.root.content_json.model_dump(),
                evidence=item.root.evidence,
                confidence=item.root.confidence,
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
            parts.append(f"- {ch.name} ({ch.role}), id={ch.id}")
            if ch.current_state:
                parts.append(f"  Previous state: {json.dumps(ch.current_state)}")
            parts.append(f"  Known: {json.dumps(ch.knowledge_known)}")
            parts.append(f"  Unknown: {json.dumps(ch.knowledge_unknown)}")
            parts.append(f"  Future locked: {json.dumps(ch.knowledge_future_locked)}")

        parts.append("")
        parts.append("## Approved World Facts")
        for fact in context.world_facts:
            parts.append(f"- {fact.name}, id={fact.id}, type={fact.entry_type}: {fact.summary}")

        parts.append("")
        parts.append(
            "Extract all state changes using exactly one of these schemas: "
            "character_state targets a character id and content_json may contain "
            "physical_state, emotional_state, current_goal, current_pressure, "
            "resources, injuries, active_secrets; "
            "character_knowledge targets a character id and content_json contains "
            "fact_key, fact_value_json, knowledge_status; "
            "timeline_event targets scene with null target id and content_json contains "
            "event_text and affected_character_ids; "
            "relationship_change targets relationship with null target id and "
            "content_json contains character_a_id, character_b_id, relation_type, "
            "description, timeline_info; "
            "world_fact_update targets an existing world_entry id and content_json may "
            "contain name, entry_type, summary, content, tags_json."
        )
        return "\n".join(parts)
