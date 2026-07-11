from __future__ import annotations

import pytest

from app.llm.base import LLMRequest, LLMResponse
from app.models.manuscript import Scene, SceneVersion
from app.services.context_builder import SceneContext
from app.services.continuity_reviewer import ContinuityReviewer
from app.services.memory_curator import MemoryCurator
from app.services.text_chunks import split_text_chunks


class TailIssueRouter:
    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        prompt = request.messages[-1].content
        if "TAIL_PROBLEM" not in prompt:
            return LLMResponse(content="[]", model="fake")
        return LLMResponse(
            content=(
                '[{"issue_type":"timeline","severity":"high",'
                '"evidence":"TAIL_PROBLEM","conflict_rule":"tail rule",'
                '"suggestion":"fix it","confidence":0.9}]'
            ),
            model="fake",
        )


class TailMemoryRouter:
    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        prompt = request.messages[-1].content
        if "TAIL_CHANGE" not in prompt:
            return LLMResponse(content="[]", model="fake")
        return LLMResponse(
            content=(
                '[{"candidate_type":"timeline_event","target_entity_type":"scene",'
                '"target_entity_id":null,"content_json":{"event_text":"TAIL_CHANGE",'
                '"affected_character_ids":[]},"evidence":"TAIL_CHANGE",'
                '"confidence":0.9}]'
            ),
            model="fake",
        )


def test_text_chunks_cover_the_entire_document_without_gaps() -> None:
    content = ("第一段。\n\n" * 800) + "TAIL_PROBLEM"
    chunks = split_text_chunks(content, max_chars=500)

    assert "".join(chunk.text for chunk in chunks) == content
    assert chunks[0].start == 0
    assert chunks[-1].end == len(content)
    assert all(left.end == right.start for left, right in zip(chunks, chunks[1:], strict=False))


@pytest.mark.asyncio
async def test_reviewer_detects_an_issue_in_the_last_chunk() -> None:
    content = ("普通正文。\n\n" * 600) + "TAIL_PROBLEM"
    scene = Scene(chapter_id="chapter-1", sequence_no=1, title="Scene")
    version = SceneVersion(
        scene_id="scene-1",
        version_no=1,
        content_markdown=content,
    )
    context = SceneContext(current_scene=scene, previous_scene=None)

    issues = await ContinuityReviewer(TailIssueRouter()).review(version, context)  # type: ignore[arg-type]

    assert len(issues) == 1
    assert issues[0].source_chunk_index > 0
    assert issues[0].source_end == len(content)


@pytest.mark.asyncio
async def test_memory_extraction_detects_a_change_in_the_last_chunk() -> None:
    content = ("普通正文。\n\n" * 600) + "TAIL_CHANGE"
    scene = Scene(chapter_id="chapter-1", sequence_no=1, title="Scene")
    version = SceneVersion(
        scene_id="scene-1",
        version_no=1,
        content_markdown=content,
    )
    context = SceneContext(current_scene=scene, previous_scene=None)

    candidates = await MemoryCurator(TailMemoryRouter()).extract(  # type: ignore[arg-type]
        version,
        context,
    )

    assert len(candidates) == 1
    assert candidates[0].source_chunk_index > 0
    assert candidates[0].source_end == len(content)
