from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import workflows as workflow_api
from app.api.memory import UpdateCandidateRequest, update_candidate
from app.llm.base import LLMRequest, LLMResponse, LLMStreamChunk
from app.llm.router import ModelResponseError
from app.models import Base
from app.models.character import Character, CharacterKnowledge, CharacterState
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.memory import MemoryCandidate
from app.models.project import NovelProject
from app.services.context_builder import ContextBuilder
from app.services.structured_output import generate_json_array
from app.workflows.scene_writing import SceneWritingWorkflow, WorkflowState


@pytest.fixture()
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'regressions.db'}",
        future=True,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as active_session:
        yield active_session
    await engine.dispose()


async def create_story_graph(
    session: AsyncSession,
    *,
    story_time_order: int = 5,
) -> tuple[NovelProject, Character, Scene, SceneVersion]:
    project = NovelProject(title="Regression story", status="active")
    session.add(project)
    await session.flush()
    character = Character(
        project_id=project.id,
        name="Lin",
        status="active",
    )
    volume = Volume(
        project_id=project.id,
        sequence_no=1,
        title="Volume",
    )
    session.add_all([character, volume])
    await session.flush()
    chapter = Chapter(
        volume_id=volume.id,
        sequence_no=1,
        title="Chapter",
    )
    session.add(chapter)
    await session.flush()
    scene = Scene(
        chapter_id=chapter.id,
        sequence_no=1,
        title="Scene",
        pov_character_id=character.id,
        story_time_order=story_time_order,
    )
    session.add(scene)
    await session.flush()
    version = SceneVersion(
        scene_id=scene.id,
        version_no=1,
        content_markdown="Draft",
    )
    session.add(version)
    await session.commit()
    return project, character, scene, version


class FailingRouter:
    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        raise RuntimeError("planned failure")


class SuccessfulRouter:
    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        return LLMResponse(content="A short plan.", model="fake")

    async def stream_generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(content_delta="Draft content", finish_reason="stop")


class PartialFailureRouter(SuccessfulRouter):
    async def stream_generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(content_delta="Partial")
        raise RuntimeError("stream failed")


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_api_scene(client: TestClient) -> dict[str, Any]:
    project = response_data(client.post("/api/projects", json={"title": "SSE story"}))
    volume = response_data(
        client.post(
            f"/api/projects/{project['id']}/volumes",
            json={"sequence_no": 1, "title": "Volume"},
        )
    )
    chapter = response_data(
        client.post(
            f"/api/volumes/{volume['id']}/chapters",
            json={"sequence_no": 1, "title": "Chapter"},
        )
    )
    return response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 1, "title": "Scene", "story_time_order": 1},
        )
    )


@pytest.mark.asyncio
async def test_workflow_error_is_not_overwritten_as_done() -> None:
    state = WorkflowState(run_id="run_test")
    workflow = SceneWritingWorkflow(
        state,
        FailingRouter(),  # type: ignore[arg-type]
        "system",
        "user",
        {},
    )

    events = [event async for event in workflow.run()]

    assert state.status == "error"
    assert [event["event"] for event in events] == ["node_start", "error"]


def test_sse_success_creates_unapproved_waiting_review_version(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = create_api_scene(client)
    monkeypatch.setattr(workflow_api, "LLMRouter", SuccessfulRouter)

    response = client.post(f"/api/scenes/{scene['id']}/generate")

    assert response.status_code == 200
    assert '"status": "waiting_review"' in response.text
    assert '"event": "version_created"' in response.text

    run_id = response.headers["x-run-id"]
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: {")
    ]
    version_created = next(e for e in events if e.get("event") == "version_created")
    assert version_created["run_id"] == run_id

    run_response = client.get(f"/api/workflows/runs/{run_id}")
    assert run_response.status_code == 200
    run_data = response_data(run_response)
    assert run_data["status"] == "waiting_review"

    versions = response_data(client.get(f"/api/scenes/{scene['id']}/versions"))
    refreshed_scene = response_data(client.get(f"/api/scenes/{scene['id']}"))
    assert len(versions) == 1
    assert versions[0]["content_markdown"] == "Draft content"
    assert refreshed_scene["approved_version_id"] is None

    assert run_data["version_created_id"] == versions[0]["id"]


def test_sse_partial_failure_does_not_create_version(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scene = create_api_scene(client)
    monkeypatch.setattr(workflow_api, "LLMRouter", PartialFailureRouter)

    response = client.post(f"/api/scenes/{scene['id']}/generate")

    assert response.status_code == 200
    assert '"event": "error"' in response.text
    versions = response_data(client.get(f"/api/scenes/{scene['id']}/versions"))
    assert versions == []


@pytest.mark.asyncio
async def test_context_excludes_future_state_and_classifies_confirmed_knowledge(
    session: AsyncSession,
) -> None:
    _, character, scene, _ = await create_story_graph(session, story_time_order=5)
    future_scene = Scene(
        chapter_id=scene.chapter_id,
        sequence_no=2,
        title="Future scene",
        story_time_order=8,
    )
    session.add(future_scene)
    await session.flush()
    future_version = SceneVersion(
        scene_id=future_scene.id,
        version_no=1,
        content_markdown="Future draft",
    )
    session.add(future_version)
    await session.flush()
    same_time_future_scene = Scene(
        chapter_id=scene.chapter_id,
        sequence_no=3,
        title="Same-time future scene",
        story_time_order=5,
    )
    session.add(same_time_future_scene)
    await session.flush()
    same_time_future_version = SceneVersion(
        scene_id=same_time_future_scene.id,
        version_no=1,
        content_markdown="Same-time future draft",
    )
    session.add(same_time_future_version)
    await session.flush()
    session.add_all(
        [
            CharacterState(
                character_id=character.id,
                timeline_order=3,
                emotional_state="past",
                status="confirmed",
            ),
            CharacterState(
                character_id=character.id,
                timeline_order=8,
                emotional_state="future",
                status="confirmed",
            ),
            CharacterState(
                character_id=character.id,
                timeline_order=4,
                emotional_state="invalidated",
                status="invalidated",
            ),
            CharacterKnowledge(
                character_id=character.id,
                fact_key="confirmed_fact",
                knowledge_status="confirmed",
            ),
            CharacterKnowledge(
                character_id=character.id,
                fact_key="unknown_fact",
                knowledge_status="unknown",
            ),
            CharacterKnowledge(
                character_id=character.id,
                fact_key="future_fact",
                knowledge_status="confirmed",
                learned_at_scene_version_id=future_version.id,
            ),
            CharacterKnowledge(
                character_id=character.id,
                fact_key="same_time_future_fact",
                knowledge_status="confirmed",
                learned_at_scene_version_id=same_time_future_version.id,
            ),
            CharacterKnowledge(
                character_id=character.id,
                fact_key="invalidated_fact",
                knowledge_status="confirmed",
                record_status="invalidated",
            ),
        ]
    )
    await session.commit()

    context = await ContextBuilder(session).build_for_scene(scene.id)

    card = context.characters[0]
    assert card.current_state is not None
    assert card.current_state["emotional_state"] == "past"
    assert card.knowledge_known == ["confirmed_fact"]
    assert card.knowledge_unknown == ["unknown_fact"]
    assert card.knowledge_future_locked == [
        "future_fact",
        "same_time_future_fact",
    ]

    review_context = await ContextBuilder(session).build_for_scene(
        scene.id,
        purpose="review",
    )
    review_locked = review_context.characters[0].knowledge_future_locked
    assert '"fact_key": "future_fact"' in review_locked[0]


@pytest.mark.asyncio
async def test_repeated_candidate_approval_is_idempotent(
    session: AsyncSession,
) -> None:
    _, character, scene, version = await create_story_graph(session, story_time_order=7)
    scene.approved_version_id = version.id
    candidate = MemoryCandidate(
        scene_version_id=version.id,
        candidate_type="character_state",
        target_entity_type="character",
        target_entity_id=character.id,
        content_json={"emotional_state": "alert"},
        evidence="He became alert.",
        confidence=0.9,
        status="pending",
    )
    session.add(candidate)
    await session.commit()
    request = Request({"type": "http", "headers": []})
    request.state.request_id = "req_test"
    payload = UpdateCandidateRequest(status="approved")

    await update_candidate(candidate.id, payload, request, session)
    await update_candidate(candidate.id, payload, request, session)

    count = await session.scalar(
        select(func.count(CharacterState.id)).where(CharacterState.character_id == character.id)
    )
    state = (
        await session.execute(select(CharacterState).where(CharacterState.character_id == character.id))
    ).scalar_one()
    assert count == 1
    assert state.timeline_order == 7


class StructuredItem(BaseModel):
    name: str


class SequenceRouter:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.calls = 0

    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        content = self.contents[min(self.calls, len(self.contents) - 1)]
        self.calls += 1
        return LLMResponse(content=content, model="fake")


@pytest.mark.asyncio
async def test_structured_output_retries_then_validates() -> None:
    router = SequenceRouter(["not json", '[{"name": "fixed"}]'])
    request = LLMRequest(messages=[])

    items = await generate_json_array(
        router,  # type: ignore[arg-type]
        "fake",
        request,
        StructuredItem,
    )

    assert router.calls == 2
    assert items[0].name == "fixed"


@pytest.mark.asyncio
async def test_structured_output_raises_after_repair_limit() -> None:
    router = SequenceRouter(["not json"])

    with pytest.raises(ModelResponseError):
        await generate_json_array(
            router,  # type: ignore[arg-type]
            "fake",
            LLMRequest(messages=[]),
            StructuredItem,
        )


def test_model_profile_api_does_not_expose_api_key(client: TestClient) -> None:
    placeholder_key = "test-api-key-placeholder"
    create_response = client.post(
        "/api/model/profiles",
        json={
            "name": "Test Profile",
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": placeholder_key,
            "model_name": "deepseek-chat",
            "is_default": True,
        },
    )
    assert create_response.status_code == 200
    created = response_data(create_response)
    assert created["api_key_configured"] is True
    assert "api_key" not in created
    assert placeholder_key not in create_response.text

    list_response = client.get("/api/model/profiles")
    assert list_response.status_code == 200
    profiles = response_data(list_response)
    listed = next(profile for profile in profiles if profile["id"] == created["id"])
    assert listed["api_key_configured"] is True
    assert "api_key" not in listed
    assert placeholder_key not in list_response.text
