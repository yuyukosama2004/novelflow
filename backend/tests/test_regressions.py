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
    timeline_order: int = 5,
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
        timeline_order=timeline_order,
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


def _parse_sse_events(text: str) -> list[dict[str, Any]]:
    """Parse SSE text stream into a list of event dicts, skipping the [DONE] sentinel."""
    events: list[dict[str, Any]] = []
    for chunk in text.strip().split("\n\n"):
        chunk = chunk.strip()
        if not chunk.startswith("data: "):
            continue
        payload = chunk[len("data: "):]
        if payload.strip() == "[DONE]":
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            pass
    return events


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
            json={"sequence_no": 1, "title": "Scene", "timeline_order": 1},
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

    # Extract X-Run-Id from response header and validate it matches the
    # version_created SSE event run_id.
    run_id = response.headers.get("x-run-id")
    assert run_id is not None, "X-Run-Id response header must be present"

    sse_events = _parse_sse_events(response.text)
    version_created_events = [e for e in sse_events if e.get("event") == "version_created"]
    assert len(version_created_events) == 1, (
        f"Expected exactly one version_created event, got {len(version_created_events)}"
    )
    assert version_created_events[0]["run_id"] == run_id, (
        f"version_created event run_id {version_created_events[0]['run_id']!r} "
        f"must match X-Run-Id header {run_id!r}"
    )

    # Query the persisted WorkflowRun and verify status and version binding.
    run_resp = client.get(f"/workflows/runs/{run_id}")
    assert run_resp.status_code == 200, (
        f"GET /workflows/runs/{run_id} failed: {run_resp.text}"
    )
    run_data = response_data(run_resp)
    assert run_data["status"] == "waiting_review", (
        f"WorkflowRun status expected waiting_review, got {run_data['status']!r}"
    )

    versions = response_data(client.get(f"/api/scenes/{scene['id']}/versions"))
    refreshed_scene = response_data(client.get(f"/api/scenes/{scene['id']}"))
    assert len(versions) == 1
    assert versions[0]["content_markdown"] == "Draft content"
    assert refreshed_scene["approved_version_id"] is None

    # The WorkflowRun version_created_id must be set and match the
    # single unapproved SceneVersion id.
    assert run_data["version_created_id"] is not None, (
        "WorkflowRun version_created_id must be set after successful generation"
    )
    assert run_data["version_created_id"] == versions[0]["id"], (
        f"WorkflowRun version_created_id {run_data['version_created_id']!r} "
        f"must match SceneVersion id {versions[0]['id']!r}"
    )


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
    _, character, scene, _ = await create_story_graph(session, timeline_order=5)
    future_scene = Scene(
        chapter_id=scene.chapter_id,
        sequence_no=2,
        title="Future scene",
        timeline_order=8,
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
        ]
    )
    await session.commit()

    context = await ContextBuilder(session).build_for_scene(scene.id)

    card = context.characters[0]
    assert card.current_state is not None
    assert card.current_state["emotional_state"] == "past"
    assert card.knowledge_known == ["confirmed_fact"]
    assert card.knowledge_unknown == ["unknown_fact"]


@pytest.mark.asyncio
async def test_repeated_candidate_approval_is_idempotent(
    session: AsyncSession,
) -> None:
    _, character, _, version = await create_story_graph(session, timeline_order=7)
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


def test_model_profile_listing_includes_api_key_configured_not_raw_key(
    client: TestClient,
) -> None:
    """Model Profile listing exposes api_key_configured (bool), never the raw api_key."""
    placeholder_key = "sk-test-placeholder-key-12345"

    # Create a model profile with a sk- format placeholder API key.
    create_resp = client.post(
        "/model/profiles",
        json={
            "name": "Test Profile",
            "provider": "deepseek",
            "base_url": "https://api.deepseek.com/v1",
            "api_key": placeholder_key,
            "model_name": "deepseek-chat",
            "is_default": True,
        },
    )
    assert create_resp.status_code == 200, (
        f"POST /model/profiles failed: {create_resp.text}"
    )
    created = response_data(create_resp)

    # The create response must expose api_key_configured, never the raw key.
    assert "api_key_configured" in created, (
        "Create response must include api_key_configured field"
    )
    assert created["api_key_configured"] is True, (
        "api_key_configured must be true when a placeholder key is set"
    )
    assert "api_key" not in created, (
        "Raw api_key must never appear in the API response"
    )
    assert placeholder_key not in create_resp.text, (
        "Placeholder API key must not leak into the raw response body"
    )

    # List all profiles and validate every profile obeys the contract.
    list_resp = client.get("/model/profiles")
    assert list_resp.status_code == 200, (
        f"GET /model/profiles failed: {list_resp.text}"
    )
    profiles = response_data(list_resp)
    assert isinstance(profiles, list), "Listing response data must be a list"
    assert len(profiles) >= 1, (
        "Expected at least one profile in the listing"
    )

    for profile in profiles:
        assert "api_key_configured" in profile, (
            "Each profile in the listing must include api_key_configured field"
        )
        assert "api_key" not in profile, (
            f"Profile {profile.get('id', '?')!r}: raw api_key must never be exposed"
        )
        # api_key_configured is a boolean derived from the stored api_key.
        assert isinstance(profile["api_key_configured"], bool), (
            f"Profile {profile.get('id', '?')!r}: "
            f"api_key_configured must be bool, got {type(profile['api_key_configured']).__name__}"
        )

    # The raw placeholder key must never appear anywhere in the listing response.
    assert placeholder_key not in list_resp.text, (
        "Placeholder API key must not leak into the listing raw response body"
    )
