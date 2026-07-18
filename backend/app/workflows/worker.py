from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import asdict
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.llm.base import LLMRequest
from app.llm.router import LLMRouter
from app.models.manuscript import Chapter, Scene, SceneVersion, Volume
from app.models.project import NovelProject
from app.models.workflow import WorkflowEvent, WorkflowRun
from app.schemas.manuscript import SceneVersionCreate, SceneVersionRead
from app.services.manuscript_service import ManuscriptService
from app.services.model_runtime import ModelRuntime, ModelRuntimeResolver
from app.services.version_summary import (
    build_version_summary_request,
    normalize_version_summary,
)
from app.workflows.runtime import LeaseLostError, WorkflowRuntime, stable_json_hash
from app.workflows.scene_writing import (
    build_draft_request,
    build_plan_request,
    perspective_warning,
)

logger = logging.getLogger(__name__)


class SceneWorkflowWorker:
    """Single local database worker for durable scene-writing runs."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        worker_id: str | None = None,
    ) -> None:
        settings = get_settings()
        self.session_factory = session_factory
        self.worker_id = worker_id or f"scene-worker-{uuid4().hex}"
        self.poll_seconds = settings.workflow_poll_seconds
        self.lease_seconds = settings.workflow_lease_seconds
        self.heartbeat_seconds = settings.workflow_heartbeat_seconds
        self.max_step_attempts = settings.workflow_max_step_attempts
        self._stop = asyncio.Event()
        self._wake = asyncio.Event()
        self._cancel_events: dict[str, asyncio.Event] = {}

    def wake(self) -> None:
        self._wake.set()

    def cancel(self, run_id: str) -> None:
        cancel_event = self._cancel_events.get(run_id)
        if cancel_event is not None:
            cancel_event.set()
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            self._wake.clear()
            if await self.run_once():
                continue
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.poll_seconds)
            except asyncio.TimeoutError:
                pass

    async def run_once(self) -> bool:
        async with self.session_factory() as session:
            claimed = await WorkflowRuntime(session).claim_next(
                self.worker_id,
                lease_seconds=self.lease_seconds,
            )
        if claimed is None:
            return False

        done = asyncio.Event()
        cancel_requested = asyncio.Event()
        self._cancel_events[claimed.id] = cancel_requested
        lease_lost = asyncio.Event()
        heartbeat_task = asyncio.create_task(
            self._maintain_lease(
                claimed.id,
                done,
                cancel_requested,
                lease_lost,
            )
        )
        try:
            if claimed.run_type != "scene_writing":
                await self._fail_run(
                    claimed.id,
                    "UNSUPPORTED_WORKFLOW",
                    f"unsupported workflow type: {claimed.run_type}",
                )
            else:
                await self._execute_scene_writing(
                    claimed.id,
                    cancel_requested,
                    lease_lost,
                )
        except asyncio.CancelledError:
            raise
        except LeaseLostError:
            logger.warning("workflow lease lost", extra={"workflow_run_id": claimed.id})
        except Exception:
            logger.exception("durable scene workflow failed")
            await self._fail_run(
                claimed.id,
                "WORKFLOW_EXECUTION_FAILED",
                "生成任务执行失败",
            )
        finally:
            done.set()
            with suppress(asyncio.CancelledError):
                await heartbeat_task
            self._cancel_events.pop(claimed.id, None)
        return True

    async def _maintain_lease(
        self,
        run_id: str,
        done: asyncio.Event,
        cancel_requested: asyncio.Event,
        lease_lost: asyncio.Event,
    ) -> None:
        while not done.is_set():
            try:
                await asyncio.wait_for(done.wait(), timeout=self.heartbeat_seconds)
                return
            except asyncio.TimeoutError:
                pass
            async with self.session_factory() as session:
                run = await session.get(WorkflowRun, run_id)
                if run is None:
                    lease_lost.set()
                    return
                if run.cancel_requested_at is not None:
                    cancel_requested.set()
                if not await WorkflowRuntime(session).heartbeat(
                    run_id,
                    self.worker_id,
                    lease_seconds=self.lease_seconds,
                ):
                    lease_lost.set()
                    return

    async def _execute_scene_writing(
        self,
        run_id: str,
        cancel_requested: asyncio.Event,
        lease_lost: asyncio.Event,
    ) -> None:
        async with self.session_factory() as session:
            runtime = WorkflowRuntime(session)
            run = await session.get(WorkflowRun, run_id)
            if run is None:
                raise LookupError(f"workflow run not found: {run_id}")
            model_runtime = await self._resolve_model_runtime(session, run)
            prompt = run.prompt_snapshot_json
            system_prompt = str(prompt.get("system", ""))
            user_prompt = str(prompt.get("user", ""))
            max_output_tokens = int(prompt.get("max_output_tokens", 4096))

            if await self._cancel_if_needed(runtime, run_id, cancel_requested):
                return
            plan_request = build_plan_request(user_prompt, run.model)
            plan, plan_ok = await self._generate_text_step(
                runtime,
                run,
                model_runtime,
                "planning",
                plan_request,
                cancel_requested,
                lease_lost,
            )
            if not plan_ok:
                return
            run.plan = plan
            await runtime.append_event(
                run_id,
                self.worker_id,
                "node_complete",
                {"node": "planning", "plan": plan, "status": "running"},
            )

            if await self._cancel_if_needed(runtime, run_id, cancel_requested):
                return
            draft_request = build_draft_request(
                system_prompt,
                user_prompt,
                plan,
                run.model,
                max_output_tokens,
            )
            draft, draft_ok = await self._generate_draft_step(
                runtime,
                run,
                model_runtime,
                draft_request,
                cancel_requested,
                lease_lost,
            )
            if not draft_ok:
                return

            summary_request = build_version_summary_request(draft, run.model)
            summary, _ = await self._generate_text_step(
                runtime,
                run,
                model_runtime,
                "summary",
                summary_request,
                cancel_requested,
                lease_lost,
                continue_on_failure=True,
                normalize=normalize_version_summary,
            )
            if await self._cancel_if_needed(runtime, run_id, cancel_requested):
                return
            await self._create_version_and_finish(
                session,
                runtime,
                run,
                draft,
                summary,
            )

    async def _generate_text_step(
        self,
        runtime: WorkflowRuntime,
        run: WorkflowRun,
        model_runtime: ModelRuntime,
        step_key: str,
        request: LLMRequest,
        cancel_requested: asyncio.Event,
        lease_lost: asyncio.Event,
        *,
        continue_on_failure: bool = False,
        normalize: Any = None,
    ) -> tuple[str, bool]:
        input_hash = self._request_hash(request, run.provider)
        step, _ = await runtime.begin_step(
            run.id,
            self.worker_id,
            step_key,
            input_hash,
        )
        if step.status == "succeeded":
            return str(step.output_json.get("content", "")), True
        if step.raw_output:
            content = step.raw_output
        else:
            await runtime.append_event(
                run.id,
                self.worker_id,
                "node_start",
                {"node": step_key, "status": "running"},
            )
            try:
                response = await model_runtime.router.generate(
                    request,
                    model_runtime.provider,
                )
            except Exception:
                logger.exception("workflow text step failed", extra={"step_key": step_key})
                retryable = step.attempt < self.max_step_attempts and not continue_on_failure
                await runtime.fail_step(
                    run.id,
                    step.id,
                    self.worker_id,
                    error_code="MODEL_CALL_FAILED",
                    error_message="生成任务执行失败",
                    retryable=retryable,
                    continue_run=continue_on_failure,
                )
                return "", continue_on_failure
            if cancel_requested.is_set() or lease_lost.is_set():
                if lease_lost.is_set():
                    raise LeaseLostError("lease lost during model call")
                await runtime.finish_run(run.id, self.worker_id, "cancelled")
                return "", False
            content = response.content
            await runtime.record_raw_output(
                run.id,
                step.id,
                self.worker_id,
                content,
            )
        normalized = normalize(content) if normalize is not None else content
        await runtime.complete_step(
            run.id,
            step.id,
            self.worker_id,
            output={"content": normalized},
            checkpoint={"next_step": self._next_step(step_key)},
        )
        return normalized, True

    async def _generate_draft_step(
        self,
        runtime: WorkflowRuntime,
        run: WorkflowRun,
        model_runtime: ModelRuntime,
        request: LLMRequest,
        cancel_requested: asyncio.Event,
        lease_lost: asyncio.Event,
    ) -> tuple[str, bool]:
        input_hash = self._request_hash(request, run.provider)
        step, created = await runtime.begin_step(
            run.id,
            self.worker_id,
            "drafting",
            input_hash,
        )
        if step.status == "succeeded":
            return str(step.output_json.get("content", "")), True
        if step.raw_output:
            draft = step.raw_output
        else:
            if created and run.draft:
                await runtime.reset_draft(run.id, self.worker_id)
            await runtime.append_event(
                run.id,
                self.worker_id,
                "node_start",
                {"node": "drafting", "status": "running"},
            )
            draft = ""
            try:
                async for chunk in model_runtime.router.stream_generate(
                    request,
                    model_runtime.provider,
                ):
                    if cancel_requested.is_set() or lease_lost.is_set():
                        if lease_lost.is_set():
                            raise LeaseLostError("lease lost during model stream")
                        await runtime.finish_run(run.id, self.worker_id, "cancelled")
                        return "", False
                    draft += chunk.content_delta
                    await runtime.append_draft_chunk(
                        run.id,
                        step.id,
                        self.worker_id,
                        chunk.content_delta,
                        chunk.finish_reason,
                    )
            except LeaseLostError:
                raise
            except Exception:
                logger.exception("workflow drafting step failed")
                await runtime.fail_step(
                    run.id,
                    step.id,
                    self.worker_id,
                    error_code="MODEL_STREAM_FAILED",
                    error_message="生成任务执行失败",
                    retryable=step.attempt < self.max_step_attempts,
                )
                return "", False
            await runtime.record_raw_output(
                run.id,
                step.id,
                self.worker_id,
                draft,
            )
        await runtime.complete_step(
            run.id,
            step.id,
            self.worker_id,
            output={"content": draft},
            checkpoint={"next_step": "summary"},
        )
        await runtime.append_event(
            run.id,
            self.worker_id,
            "node_complete",
            {"node": "drafting", "content": draft, "status": "running"},
        )
        return draft, True

    async def _create_version_and_finish(
        self,
        session: AsyncSession,
        runtime: WorkflowRuntime,
        run: WorkflowRun,
        draft: str,
        summary: str,
    ) -> None:
        manuscript = ManuscriptService(session)
        version = await session.get(SceneVersion, run.version_created_id) if run.version_created_id else None
        if version is None:
            generation_mode = str(run.prompt_snapshot_json.get("generation_mode", "new"))
            version = await manuscript.add_version(
                run.scene_id,
                SceneVersionCreate(
                    content_markdown=draft,
                    summary=summary,
                    source_type=("ai_generated" if generation_mode == "new" else "ai_revised"),
                    model_profile_id=run.model_profile_id,
                    prompt_snapshot_json=run.prompt_snapshot_json,
                    context_manifest_json=run.context_manifest_json,
                ),
            )
            run.version_created_id = version.id
            run.final_content = draft
            await session.commit()

        if not await self._has_event(session, run.id, "version_created"):
            project = await self._project_for_scene(session, run.scene_id)
            event_payload: dict[str, Any] = {
                "status": "waiting_review",
                "version": SceneVersionRead.model_validate(version).model_dump(mode="json"),
            }
            warning = perspective_warning(draft, project.pov_type)
            if warning:
                event_payload["perspective_warning"] = warning
            await runtime.append_event(
                run.id,
                self.worker_id,
                "version_created",
                event_payload,
            )
        await runtime.finish_run(run.id, self.worker_id, "waiting_review")

    async def _cancel_if_needed(
        self,
        runtime: WorkflowRuntime,
        run_id: str,
        cancel_requested: asyncio.Event,
    ) -> bool:
        if not cancel_requested.is_set():
            run = await runtime.session.get(WorkflowRun, run_id)
            if run is not None and run.cancel_requested_at is not None:
                cancel_requested.set()
        if cancel_requested.is_set():
            await runtime.finish_run(run_id, self.worker_id, "cancelled")
            return True
        return False

    async def _resolve_model_runtime(
        self,
        session: AsyncSession,
        run: WorkflowRun,
    ) -> ModelRuntime:
        if run.model_profile_id is not None:
            return await ModelRuntimeResolver(session).resolve_for_scene(
                run.scene_id,
                run.model_profile_id,
            )
        return ModelRuntime(
            router=LLMRouter(),
            profile_id=None,
            provider=run.provider,
            model=run.model,
        )

    async def _fail_run(self, run_id: str, error_code: str, error_message: str) -> None:
        async with self.session_factory() as session:
            try:
                await WorkflowRuntime(session).fail_run(
                    run_id,
                    self.worker_id,
                    error_code=error_code,
                    error_message=error_message,
                )
            except LeaseLostError:
                pass

    @staticmethod
    async def _project_for_scene(
        session: AsyncSession,
        scene_id: str,
    ) -> NovelProject:
        project = (
            await session.execute(
                select(NovelProject)
                .join(Volume, Volume.project_id == NovelProject.id)
                .join(Chapter, Chapter.volume_id == Volume.id)
                .join(Scene, Scene.chapter_id == Chapter.id)
                .where(Scene.id == scene_id)
            )
        ).scalar_one()
        return project

    @staticmethod
    async def _has_event(
        session: AsyncSession,
        run_id: str,
        event_type: str,
    ) -> bool:
        return (
            await session.scalar(
                select(WorkflowEvent.id)
                .where(
                    WorkflowEvent.workflow_run_id == run_id,
                    WorkflowEvent.event_type == event_type,
                )
                .limit(1)
            )
            is not None
        )

    @staticmethod
    def _request_hash(request: LLMRequest, provider: str) -> str:
        return stable_json_hash({"provider": provider, "request": asdict(request)})

    @staticmethod
    def _next_step(step_key: str) -> str:
        return {"planning": "drafting", "summary": "version"}.get(step_key, "")
