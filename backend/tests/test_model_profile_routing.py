from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api import memory as memory_api
from app.api import review as review_api
from app.llm.deepseek import DeepSeekClient
from app.llm.fake import FakeLLMClient
from app.llm.ollama import OllamaClient
from app.llm.openai_compatible import OpenAICompatibleClient
from app.llm.router import LLMRouter, ModelConfigurationError
from app.models import Base
from app.models.memory import MemoryCandidate
from app.models.model_profile import ModelProfile
from app.models.project import NovelProject
from app.services import outline_service
from app.services.model_profile_service import ModelProfileService
from app.services.model_runtime import ModelRuntimeResolver


@pytest.fixture()
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'model-routing.db'}",
        future=True,
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as active_session:
        yield active_session
    await engine.dispose()


@pytest.mark.parametrize(
    ("provider", "expected_type", "base_url", "model_name"),
    [
        ("deepseek", DeepSeekClient, "https://deepseek.example", "deepseek-chat"),
        (
            "openai_compatible",
            OpenAICompatibleClient,
            "https://compatible.example/v1",
            "custom-model",
        ),
        ("ollama", OllamaClient, "http://ollama.example", "qwen3"),
        ("fake", FakeLLMClient, "", "fake-model"),
    ],
)
def test_router_builds_client_from_profile(
    provider: str,
    expected_type: type,
    base_url: str,
    model_name: str,
) -> None:
    profile = ModelProfile(
        name=provider,
        provider=provider,
        base_url=base_url,
        api_key="profile-secret",
        model_name=model_name,
        timeout_seconds=37,
        enabled=True,
    )

    client = LLMRouter.client_from_profile(profile)

    assert isinstance(client, expected_type)
    if provider != "fake":
        assert client.base_url == base_url.rstrip("/")
        assert client.default_model == model_name
        assert client.timeout_seconds == 37


@pytest.mark.asyncio
async def test_runtime_resolution_priority_and_disabled_guard(
    session: AsyncSession,
) -> None:
    system_default = ModelProfile(
        name="system",
        provider="fake",
        model_name="system-model",
        is_default=True,
        enabled=True,
    )
    project_default = ModelProfile(
        name="project",
        provider="fake",
        model_name="project-model",
        enabled=True,
    )
    requested = ModelProfile(
        name="requested",
        provider="fake",
        model_name="requested-model",
        enabled=True,
    )
    disabled = ModelProfile(
        name="disabled",
        provider="fake",
        model_name="disabled-model",
        enabled=False,
    )
    session.add_all([system_default, project_default, requested, disabled])
    await session.flush()
    project = NovelProject(
        title="Routing story",
        default_model_profile_id=project_default.id,
    )
    session.add(project)
    await session.commit()

    resolver = ModelRuntimeResolver(session)
    explicit = await resolver.resolve(project.id, requested.id)
    project_choice = await resolver.resolve(project.id, None)
    project.default_model_profile_id = None
    await session.commit()
    system_choice = await resolver.resolve(project.id, None)

    assert explicit.profile_id == requested.id
    assert explicit.model == "requested-model"
    assert project_choice.profile_id == project_default.id
    assert project_choice.model == "project-model"
    assert system_choice.profile_id == system_default.id
    assert system_choice.model == "system-model"

    with pytest.raises(ModelConfigurationError):
        await resolver.resolve(project.id, disabled.id)


@pytest.mark.asyncio
async def test_empty_api_key_update_preserves_existing_secret(
    session: AsyncSession,
) -> None:
    service = ModelProfileService(session)
    profile = await service.create(
        {
            "name": "Secret profile",
            "provider": "deepseek",
            "api_key": "keep-me",
        }
    )

    updated = await service.update(profile.id, {"name": "Renamed", "api_key": ""})

    assert updated.name == "Renamed"
    assert updated.api_key == "keep-me"


@pytest.mark.asyncio
async def test_profile_connection_failure_never_returns_api_key(
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = ModelProfileService(session)
    profile = await service.create(
        {
            "name": "Broken profile",
            "provider": "deepseek",
            "base_url": "https://invalid.example",
            "api_key": "do-not-leak-this-key",
            "model_name": "deepseek-chat",
        }
    )

    async def fail_connection(self: DeepSeekClient) -> bool:
        raise RuntimeError(f"request failed with {self.api_key}")

    monkeypatch.setattr(DeepSeekClient, "validate_connection", fail_connection)
    result = await service.test(profile.id)

    assert result["connected"] is False
    assert "do-not-leak-this-key" not in str(result)


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_api_story(client: TestClient) -> tuple[dict[str, Any], dict[str, Any]]:
    project = response_data(client.post("/api/projects", json={"title": "Profile story"}))
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
    scene = response_data(
        client.post(
            f"/api/chapters/{chapter['id']}/scenes",
            json={"sequence_no": 1, "title": "Scene"},
        )
    )
    version = response_data(
        client.post(
            f"/api/scenes/{scene['id']}/versions",
            json={"content_markdown": "The bell rang."},
        )
    )
    return scene, version


class EmptyReviewer:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "review prompt"

    async def review(self, *_: Any) -> list[Any]:
        return []


class EmptyCurator:
    def __init__(self, *_: Any, **__: Any) -> None:
        pass

    def build_prompt(self, *_: Any) -> str:
        return "memory prompt"

    async def extract(self, *_: Any) -> list[MemoryCandidate]:
        return []


def create_fake_profile(client: TestClient) -> dict[str, Any]:
    return response_data(
        client.post(
            "/api/model/profiles",
            json={
                "name": "Test fake",
                "provider": "fake",
                "model_name": "profile-fake-model",
                "enabled": True,
            },
        )
    )


def test_review_and_memory_runs_record_requested_profile(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, version = create_api_story(client)
    profile = create_fake_profile(client)
    monkeypatch.setattr(review_api, "ContinuityReviewer", EmptyReviewer)
    monkeypatch.setattr(memory_api, "MemoryCurator", EmptyCurator)

    review = response_data(
        client.post(
            f"/api/scene-versions/{version['id']}/review",
            json={"model_profile_id": profile["id"]},
        )
    )
    memory = response_data(
        client.post(
            f"/api/scene-versions/{version['id']}/extract-memories",
            json={"model_profile_id": profile["id"]},
        )
    )

    for run in (review["run"], memory["run"]):
        assert run["model_profile_id"] == profile["id"]
        assert run["provider"] == "fake"
        assert run["model"] == "profile-fake-model"


def test_scene_workflow_uses_and_records_requested_profile(
    client: TestClient,
) -> None:
    scene, _ = create_api_story(client)
    profile = create_fake_profile(client)

    response = client.post(
        f"/api/scenes/{scene['id']}/generate",
        json={"model_profile_id": profile["id"]},
    )
    assert response.status_code == 200, response.text
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: {")
    ]
    run_id = events[0]["run_id"]
    run = response_data(client.get(f"/api/workflows/runs/{run_id}"))
    versions = response_data(client.get(f"/api/scenes/{scene['id']}/versions"))

    assert run["model_profile_id"] == profile["id"]
    assert run["provider"] == "fake"
    assert run["model"] == "profile-fake-model"
    assert versions[0]["model_profile_id"] == profile["id"]


def test_interview_session_keeps_requested_profile(client: TestClient) -> None:
    project = response_data(client.post("/api/projects", json={"title": "Interview story"}))
    profile = create_fake_profile(client)

    started = response_data(
        client.post(
            f"/api/projects/{project['id']}/interview/start",
            json={
                "entry_type": "idea",
                "model_profile_id": profile["id"],
            },
        )
    )
    continued = response_data(
        client.post(
            f"/api/sessions/{started['id']}/message",
            json={"content": "我想写一个关于选择的故事。"},
        )
    )

    assert started["model_profile_id"] == profile["id"]
    assert started["provider"] == "fake"
    assert started["model"] == "profile-fake-model"
    assert continued["model_profile_id"] == profile["id"]


def test_outline_generation_uses_requested_profile(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = response_data(client.post("/api/projects", json={"title": "Outline story"}))
    profile = create_fake_profile(client)
    captured: dict[str, Any] = {}

    async def fake_generate(router: Any, provider: str, request: Any, *_: Any) -> list[Any]:
        captured.update(
            profile_id=router.profile.id if router.profile else None,
            provider=provider,
            model=request.model,
        )
        return []

    monkeypatch.setattr(outline_service, "generate_json_array", fake_generate)
    outline = response_data(
        client.post(
            f"/api/projects/{project['id']}/generate-outline",
            json={"model_profile_id": profile["id"]},
        )
    )

    assert outline == []
    assert captured == {
        "profile_id": profile["id"],
        "provider": "fake",
        "model": "profile-fake-model",
    }
