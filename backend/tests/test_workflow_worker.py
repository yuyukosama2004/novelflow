from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.llm.base import LLMRequest, LLMResponse, LLMStreamChunk
from app.models import Base
from app.models.base import utc_now
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.project import NovelProject
from app.models.workflow import WorkflowRun, WorkflowStepRun
from app.workflows import worker as worker_module
from app.workflows.runtime import WorkflowRuntime, stable_json_hash
from app.workflows.worker import SceneWorkflowWorker


class CountingRouter:
    generate_calls = 0
    stream_calls = 0

    @classmethod
    def reset(cls) -> None:
        cls.generate_calls = 0
        cls.stream_calls = 0

    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        type(self).generate_calls += 1
        content = "摘要：恢复计划\n节拍：开始，转折，收束"
        if request.max_tokens == 80:
            content = "走廊重逢暗藏戒备"
        return LLMResponse(content=content, model="fake")

    async def stream_generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> AsyncIterator[LLMStreamChunk]:
        type(self).stream_calls += 1
        yield LLMStreamChunk(content_delta="第一段。")
        yield LLMStreamChunk(content_delta="第二段。", finish_reason="stop")


class CancellableRouter:
    started: asyncio.Event
    release: asyncio.Event

    async def generate(self, request: LLMRequest, provider: str = "") -> LLMResponse:
        return LLMResponse(content="摘要：取消测试\n节拍：开始", model="fake")

    async def stream_generate(
        self,
        request: LLMRequest,
        provider: str = "",
    ) -> AsyncIterator[LLMStreamChunk]:
        yield LLMStreamChunk(content_delta="已持久化的第一段。")
        type(self).started.set()
        await type(self).release.wait()
        yield LLMStreamChunk(content_delta="取消后不应保存的第二段。", finish_reason="stop")


def response_data(response: Any) -> Any:
    assert response.status_code < 400, response.text
    return response.json()["data"]


def create_api_scene(client: TestClient) -> dict[str, Any]:
    project = response_data(client.post("/api/projects", json={"title": "Durable SSE"}))
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
            json={"sequence_no": 1, "title": "Scene"},
        )
    )


def sse_events(response_text: str) -> list[dict[str, Any]]:
    return [
        json.loads(line[6:])
        for line in response_text.splitlines()
        if line.startswith("data: ") and line != "data: [DONE]"
    ]


def test_idempotent_generation_replays_persisted_events_without_model_reexecution(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    CountingRouter.reset()
    monkeypatch.setattr(worker_module, "LLMRouter", CountingRouter)
    scene = create_api_scene(client)
    payload = {
        "idempotency_key": "same-browser-request",
        "target_word_count": 800,
    }

    first = client.post(f"/api/scenes/{scene['id']}/generate", json=payload)
    run_id = first.headers["x-run-id"]
    first_events = sse_events(first.text)
    middle_event_id = first_events[len(first_events) // 2]["event_id"]
    resumed = client.get(
        f"/api/workflows/runs/{run_id}/events",
        headers={"Last-Event-ID": str(middle_event_id)},
    )
    second = client.post(f"/api/scenes/{scene['id']}/generate", json=payload)

    assert first.status_code == 200
    assert '"event": "version_created"' in first.text
    assert second.headers["x-run-id"] == run_id
    assert all(event["event_id"] > middle_event_id for event in sse_events(resumed.text))
    assert CountingRouter.generate_calls == 2  # planning and summary
    assert CountingRouter.stream_calls == 1
    versions = response_data(client.get(f"/api/scenes/{scene['id']}/versions"))
    runs = response_data(client.get(f"/api/scenes/{scene['id']}/workflow-runs"))
    assert len(versions) == 1
    assert len(runs) == 1
    assert runs[0]["last_event_sequence"] == first_events[-1]["event_id"]
    assert not any(event["event"] == "content_delta" for event in runs[0]["events_json"])


@pytest.mark.asyncio
async def test_worker_reuses_raw_plan_recorded_before_previous_process_crash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'worker.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        project = NovelProject(title="Crash recovery")
        volume = Volume(project=project, sequence_no=1, title="Volume")
        chapter = Chapter(volume=volume, sequence_no=1, title="Chapter")
        scene = Scene(chapter=chapter, sequence_no=1, title="Scene")
        session.add(scene)
        await session.commit()
        runtime = WorkflowRuntime(session)
        run, _ = await runtime.enqueue(
            scene_id=scene.id,
            run_type="scene_writing",
            idempotency_key=stable_json_hash({"crash": "planning"}),
            input_payload={"scene_id": scene.id},
            provider="fake",
            model="fake",
            prompt_snapshot={
                "system": "system",
                "user": "user",
                "generation_mode": "new",
                "max_output_tokens": 1024,
            },
        )
        assert await runtime.claim_next("crashed-worker") is not None
        plan_request_hash = SceneWorkflowWorker._request_hash(
            worker_module.build_plan_request("user", "fake"),
            "fake",
        )
        step, _ = await runtime.begin_step(
            run.id,
            "crashed-worker",
            "planning",
            plan_request_hash,
        )
        await runtime.record_raw_output(
            run.id,
            step.id,
            "crashed-worker",
            "摘要：已落盘计划\n节拍：恢复后继续",
        )
        run.lease_expires_at = utc_now() - timedelta(seconds=1)
        await session.commit()

    CountingRouter.reset()
    monkeypatch.setattr(worker_module, "LLMRouter", CountingRouter)
    worker = SceneWorkflowWorker(factory, worker_id="recovery-worker")
    assert await worker.run_once() is True

    async with factory() as session:
        persisted = await session.get(WorkflowRun, run.id)
        assert persisted is not None
        assert persisted.status == "waiting_review"
        assert persisted.plan == "摘要：已落盘计划\n节拍：恢复后继续"
        assert await session.scalar(select(func.count()).select_from(SceneVersion)) == 1
        planning_steps = (
            (
                await session.execute(
                    select(WorkflowStepRun).where(
                        WorkflowStepRun.workflow_run_id == run.id,
                        WorkflowStepRun.step_key == "planning",
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(planning_steps) == 1
        assert planning_steps[0].status == "succeeded"
    assert CountingRouter.generate_calls == 1  # summary only; planning was not repeated
    assert CountingRouter.stream_calls == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_cancellation_stops_before_version_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'cancel.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        project = NovelProject(title="Cancellation")
        volume = Volume(project=project, sequence_no=1, title="Volume")
        chapter = Chapter(volume=volume, sequence_no=1, title="Chapter")
        scene = Scene(chapter=chapter, sequence_no=1, title="Scene")
        session.add(scene)
        await session.commit()
        run, _ = await WorkflowRuntime(session).enqueue(
            scene_id=scene.id,
            run_type="scene_writing",
            idempotency_key=stable_json_hash({"cancel": True}),
            input_payload={"scene_id": scene.id},
            provider="fake",
            model="fake",
            prompt_snapshot={
                "system": "system",
                "user": "user",
                "generation_mode": "new",
                "max_output_tokens": 1024,
            },
        )

    CancellableRouter.started = asyncio.Event()
    CancellableRouter.release = asyncio.Event()
    monkeypatch.setattr(worker_module, "LLMRouter", CancellableRouter)
    worker = SceneWorkflowWorker(factory, worker_id="cancel-worker")
    worker_task = asyncio.create_task(worker.run_once())
    await asyncio.wait_for(CancellableRouter.started.wait(), timeout=2)
    worker.cancel(run.id)
    CancellableRouter.release.set()
    assert await worker_task is True

    async with factory() as session:
        persisted = await session.get(WorkflowRun, run.id)
        assert persisted is not None
        assert persisted.status == "cancelled"
        assert persisted.draft == "已持久化的第一段。"
        assert persisted.version_created_id is None
        assert await session.scalar(select(func.count()).select_from(SceneVersion)) == 0
    await engine.dispose()
