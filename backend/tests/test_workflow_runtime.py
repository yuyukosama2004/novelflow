from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base
from app.models.base import utc_now
from app.models.manuscript import Chapter, Scene, Volume
from app.models.project import NovelProject
from app.models.workflow import WorkflowEvent, WorkflowRun, WorkflowStepRun
from app.workflows.runtime import LeaseLostError, WorkflowRuntime, stable_json_hash


@pytest.fixture()
async def session(tmp_path: Path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'runtime.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


async def create_scene(session: AsyncSession) -> Scene:
    project = NovelProject(title="Durable workflow")
    volume = Volume(project=project, sequence_no=1, title="Volume")
    chapter = Chapter(volume=volume, sequence_no=1, title="Chapter")
    scene = Scene(chapter=chapter, sequence_no=1, title="Scene")
    session.add(scene)
    await session.commit()
    return scene


async def enqueue(runtime: WorkflowRuntime, scene_id: str) -> WorkflowRun:
    run, created = await runtime.enqueue(
        scene_id=scene_id,
        run_type="scene_writing",
        idempotency_key=stable_json_hash({"scene_id": scene_id, "revision": 1}),
        input_payload={"scene_id": scene_id, "revision": 1},
    )
    assert created is True
    return run


@pytest.mark.asyncio
async def test_enqueue_is_idempotent(session: AsyncSession) -> None:
    scene = await create_scene(session)
    runtime = WorkflowRuntime(session)
    payload = {"scene_id": scene.id, "revision": 1}
    key = stable_json_hash(payload)

    first, first_created = await runtime.enqueue(
        scene_id=scene.id,
        run_type="scene_writing",
        idempotency_key=key,
        input_payload=payload,
    )
    second, second_created = await runtime.enqueue(
        scene_id=scene.id,
        run_type="scene_writing",
        idempotency_key=key,
        input_payload=payload,
    )

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert await session.scalar(select(func.count()).select_from(WorkflowRun)) == 1


@pytest.mark.asyncio
async def test_concurrent_workers_cannot_both_claim_the_same_run(tmp_path: Path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'race.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as setup_session:
        scene = await create_scene(setup_session)
        run = await enqueue(WorkflowRuntime(setup_session), scene.id)

    async with factory() as first_session, factory() as second_session:
        claims = await asyncio.gather(
            WorkflowRuntime(first_session).claim_next("worker-a"),
            WorkflowRuntime(second_session).claim_next("worker-b"),
        )

    assert [claim.id for claim in claims if claim is not None] == [run.id]
    async with factory() as verification_session:
        persisted = await verification_session.get(WorkflowRun, run.id)
        assert persisted is not None
        assert persisted.attempt == 1
        assert persisted.lease_owner in {"worker-a", "worker-b"}
    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_lease_is_reclaimed_and_old_owner_is_fenced(
    session: AsyncSession,
) -> None:
    scene = await create_scene(session)
    runtime = WorkflowRuntime(session)
    run = await enqueue(runtime, scene.id)

    first_claim = await runtime.claim_next("worker-a", lease_seconds=60)
    assert first_claim is not None
    assert first_claim.id == run.id
    assert first_claim.attempt == 1
    assert await runtime.claim_next("worker-b", lease_seconds=60) is None
    assert await runtime.heartbeat(run.id, "worker-a", lease_seconds=60) is True

    first_claim.lease_expires_at = utc_now() - timedelta(seconds=1)
    await session.commit()
    second_claim = await runtime.claim_next("worker-b", lease_seconds=60)

    assert second_claim is not None
    assert second_claim.id == run.id
    assert second_claim.attempt == 2
    assert second_claim.lease_owner == "worker-b"
    assert await runtime.heartbeat(run.id, "worker-a", lease_seconds=60) is False
    with pytest.raises(LeaseLostError):
        await runtime.begin_step(run.id, "worker-a", "planning", stable_json_hash({"x": 1}))


@pytest.mark.asyncio
async def test_recorded_model_output_and_completed_step_survive_reclaim(
    session: AsyncSession,
) -> None:
    scene = await create_scene(session)
    runtime = WorkflowRuntime(session)
    run = await enqueue(runtime, scene.id)
    assert await runtime.claim_next("worker-a", lease_seconds=60) is not None
    input_hash = stable_json_hash({"prompt": "write"})

    step, created = await runtime.begin_step(run.id, "worker-a", "planning", input_hash)
    assert created is True
    await runtime.record_raw_output(run.id, step.id, "worker-a", "raw model result")

    run.lease_expires_at = utc_now() - timedelta(seconds=1)
    await session.commit()
    assert await runtime.claim_next("worker-b", lease_seconds=60) is not None
    recovered, recovered_created = await runtime.begin_step(
        run.id,
        "worker-b",
        "planning",
        input_hash,
    )

    assert recovered_created is False
    assert recovered.id == step.id
    assert recovered.raw_output == "raw model result"
    assert recovered.worker_id == "worker-b"

    completed = await runtime.complete_step(
        run.id,
        recovered.id,
        "worker-b",
        output={"plan": "structured"},
        checkpoint={"next_step": "drafting"},
    )
    reused, reused_created = await runtime.begin_step(
        run.id,
        "worker-b",
        "planning",
        input_hash,
    )
    await runtime.finish_run(run.id, "worker-b", "waiting_review")

    assert completed.status == "succeeded"
    assert completed.raw_output_hash == hashlib.sha256(b"raw model result").hexdigest()
    assert completed.output_hash == stable_json_hash({"plan": "structured"})
    assert reused_created is False
    assert reused.id == completed.id
    assert await session.scalar(select(func.count()).select_from(WorkflowStepRun)) == 1
    events = (
        await session.execute(
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_run_id == run.id)
            .order_by(WorkflowEvent.sequence_no)
        )
    ).scalars()
    assert [(event.sequence_no, event.event_type) for event in events] == [
        (1, "step_completed"),
        (2, "workflow_finished"),
    ]


@pytest.mark.asyncio
async def test_retryable_step_failure_requeues_with_a_new_attempt(
    session: AsyncSession,
) -> None:
    scene = await create_scene(session)
    runtime = WorkflowRuntime(session)
    run = await enqueue(runtime, scene.id)
    assert await runtime.claim_next("worker-a") is not None
    input_hash = stable_json_hash({"prompt": "retry"})
    first_step, _ = await runtime.begin_step(
        run.id,
        "worker-a",
        "drafting",
        input_hash,
    )

    failed = await runtime.fail_step(
        run.id,
        first_step.id,
        "worker-a",
        error_code="MODEL_TIMEOUT",
        error_message="model timed out",
        retryable=True,
    )
    reclaimed = await runtime.claim_next("worker-b")
    second_step, created = await runtime.begin_step(
        run.id,
        "worker-b",
        "drafting",
        input_hash,
    )

    assert failed.status == "failed"
    assert failed.retryable is True
    assert reclaimed is not None
    assert reclaimed.attempt == 2
    assert created is True
    assert second_step.attempt == 2
    assert second_step.id != first_step.id
