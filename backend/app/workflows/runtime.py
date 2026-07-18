from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from typing import Any, cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utc_now
from app.models.workflow import WorkflowEvent, WorkflowRun, WorkflowStepRun

TERMINAL_RUN_STATUSES = frozenset({"waiting_review", "succeeded", "failed", "cancelled", "error"})


class LeaseLostError(RuntimeError):
    pass


def stable_json_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class WorkflowRuntime:
    """Transactional queue primitives for the local durable workflow worker."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
        self,
        *,
        scene_id: str,
        run_type: str,
        idempotency_key: str,
        input_payload: dict[str, Any],
        model_profile_id: str | None = None,
        provider: str = "",
        model: str = "",
        prompt_snapshot: dict[str, Any] | None = None,
        context_manifest: dict[str, Any] | None = None,
    ) -> tuple[WorkflowRun, bool]:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")
        existing = await self._run_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False

        run = WorkflowRun(
            scene_id=scene_id,
            run_type=run_type,
            status="queued",
            idempotency_key=idempotency_key,
            input_hash=stable_json_hash(input_payload),
            model_profile_id=model_profile_id,
            provider=provider,
            model=model,
            prompt_snapshot_json=prompt_snapshot or {},
            context_manifest_json=context_manifest or {},
        )
        self.session.add(run)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self._run_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing, False
            raise
        return run, True

    async def claim_next(
        self,
        worker_id: str,
        *,
        lease_seconds: int = 30,
    ) -> WorkflowRun | None:
        self._validate_lease_arguments(worker_id, lease_seconds)
        now = utc_now()
        claimable = or_(
            WorkflowRun.status == "queued",
            and_(
                WorkflowRun.status == "running",
                WorkflowRun.lease_expires_at.is_not(None),
                WorkflowRun.lease_expires_at <= now,
            ),
        )
        candidate_ids = (
            await self.session.execute(
                select(WorkflowRun.id)
                .where(
                    claimable,
                    WorkflowRun.cancel_requested_at.is_(None),
                )
                .order_by(WorkflowRun.created_at, WorkflowRun.id)
                .limit(10)
            )
        ).scalars()
        for run_id in candidate_ids:
            result = cast(
                CursorResult[Any],
                await self.session.execute(
                    update(WorkflowRun)
                    .where(
                        WorkflowRun.id == run_id,
                        claimable,
                        WorkflowRun.cancel_requested_at.is_(None),
                    )
                    .values(
                        status="running",
                        lease_owner=worker_id,
                        lease_expires_at=now + timedelta(seconds=lease_seconds),
                        heartbeat_at=now,
                        attempt=WorkflowRun.attempt + 1,
                    )
                ),
            )
            if result.rowcount == 1:
                await self.session.commit()
                return await self.session.get(WorkflowRun, run_id)
        await self.session.commit()
        return None

    async def heartbeat(
        self,
        run_id: str,
        worker_id: str,
        *,
        lease_seconds: int = 30,
    ) -> bool:
        self._validate_lease_arguments(worker_id, lease_seconds)
        now = utc_now()
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(WorkflowRun)
                .where(
                    WorkflowRun.id == run_id,
                    WorkflowRun.status == "running",
                    WorkflowRun.lease_owner == worker_id,
                    WorkflowRun.lease_expires_at > now,
                )
                .values(
                    heartbeat_at=now,
                    lease_expires_at=now + timedelta(seconds=lease_seconds),
                )
            ),
        )
        await self.session.commit()
        return result.rowcount == 1

    async def begin_step(
        self,
        run_id: str,
        worker_id: str,
        step_key: str,
        input_hash: str,
    ) -> tuple[WorkflowStepRun, bool]:
        run = await self._leased_run(run_id, worker_id)
        latest = (
            await self.session.execute(
                select(WorkflowStepRun)
                .where(
                    WorkflowStepRun.workflow_run_id == run_id,
                    WorkflowStepRun.step_key == step_key,
                    WorkflowStepRun.input_hash == input_hash,
                )
                .order_by(WorkflowStepRun.attempt.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if latest is not None and latest.status == "succeeded":
            return latest, False
        if latest is not None and latest.status == "running":
            if latest.worker_id == worker_id or latest.raw_output:
                latest.worker_id = worker_id
                run.current_step_key = step_key
                await self.session.commit()
                return latest, False
            latest.status = "interrupted"
            latest.completed_at = utc_now()

        maximum_attempt = await self.session.scalar(
            select(func.max(WorkflowStepRun.attempt)).where(
                WorkflowStepRun.workflow_run_id == run_id,
                WorkflowStepRun.step_key == step_key,
            )
        )
        step = WorkflowStepRun(
            workflow_run_id=run_id,
            step_key=step_key,
            attempt=(maximum_attempt or 0) + 1,
            worker_id=worker_id,
            status="running",
            input_hash=input_hash,
            started_at=utc_now(),
        )
        run.current_step_key = step_key
        self.session.add(step)
        await self.session.commit()
        return step, True

    async def record_raw_output(
        self,
        run_id: str,
        step_id: str,
        worker_id: str,
        raw_output: str,
    ) -> WorkflowStepRun:
        await self._leased_run(run_id, worker_id)
        step = await self._running_step(run_id, step_id, worker_id)
        step.raw_output = raw_output
        step.raw_output_hash = hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
        await self.session.commit()
        return step

    async def complete_step(
        self,
        run_id: str,
        step_id: str,
        worker_id: str,
        *,
        output: dict[str, Any],
        checkpoint: dict[str, Any],
    ) -> WorkflowStepRun:
        run = await self._leased_run(run_id, worker_id)
        step = await self._running_step(run_id, step_id, worker_id)
        step.output_json = output
        step.output_hash = stable_json_hash(output)
        step.checkpoint_json = checkpoint
        step.status = "succeeded"
        step.completed_at = utc_now()
        run.current_step_key = ""
        run.last_healthy_step_key = step.step_key
        await self._append_event_without_commit(
            run_id,
            "step_completed",
            {
                "step_key": step.step_key,
                "attempt": step.attempt,
                "output_hash": step.output_hash,
            },
        )
        await self.session.commit()
        return step

    async def fail_step(
        self,
        run_id: str,
        step_id: str,
        worker_id: str,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        continue_run: bool = False,
    ) -> WorkflowStepRun:
        run = await self._leased_run(run_id, worker_id)
        step = await self._running_step(run_id, step_id, worker_id)
        step.status = "failed"
        step.error_code = error_code
        step.error_message = error_message
        step.retryable = retryable
        step.completed_at = utc_now()
        run.current_step_key = ""
        if not continue_run:
            run.status = "queued" if retryable else "failed"
            run.error = error_message
            self._clear_lease(run)
        await self._append_event_without_commit(
            run_id,
            "step_failed",
            {
                "step_key": step.step_key,
                "attempt": step.attempt,
                "error_code": error_code,
                "retryable": retryable,
            },
        )
        if not retryable and not continue_run:
            await self._append_event_without_commit(
                run_id,
                "error",
                {"error": error_message, "error_code": error_code},
            )
        await self.session.commit()
        return step

    async def append_draft_chunk(
        self,
        run_id: str,
        step_id: str,
        worker_id: str,
        content_delta: str,
        finish_reason: str | None,
    ) -> WorkflowRun:
        run = await self._leased_run(run_id, worker_id)
        step = await self._running_step(run_id, step_id, worker_id)
        run.draft += content_delta
        if finish_reason is not None:
            step.raw_output = run.draft
            step.raw_output_hash = hashlib.sha256(run.draft.encode("utf-8")).hexdigest()
        await self._append_event_without_commit(
            run_id,
            "content_delta",
            {
                "content_delta": content_delta,
                "finish_reason": finish_reason,
                "status": "running",
            },
        )
        await self.session.commit()
        return run

    async def reset_draft(
        self,
        run_id: str,
        worker_id: str,
    ) -> WorkflowRun:
        run = await self._leased_run(run_id, worker_id)
        run.draft = ""
        await self._append_event_without_commit(
            run_id,
            "draft_reset",
            {"status": "running"},
        )
        await self.session.commit()
        return run

    async def append_event(
        self,
        run_id: str,
        worker_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> WorkflowEvent:
        await self._leased_run(run_id, worker_id)
        event = await self._append_event_without_commit(run_id, event_type, payload)
        await self.session.commit()
        return event

    async def finish_run(
        self,
        run_id: str,
        worker_id: str,
        status: str,
    ) -> WorkflowRun:
        if status not in TERMINAL_RUN_STATUSES:
            raise ValueError(f"invalid terminal workflow status: {status}")
        run = await self._leased_run(run_id, worker_id)
        run.status = status
        run.current_step_key = ""
        self._clear_lease(run)
        await self._append_event_without_commit(run_id, "workflow_finished", {"status": status})
        await self.session.commit()
        return run

    async def fail_run(
        self,
        run_id: str,
        worker_id: str,
        *,
        error_code: str,
        error_message: str,
    ) -> WorkflowRun:
        run = await self._leased_run(run_id, worker_id)
        run.status = "failed"
        run.error = error_message
        run.blocked_reason = error_code
        run.current_step_key = ""
        self._clear_lease(run)
        await self._append_event_without_commit(
            run_id,
            "error",
            {"error": error_message, "error_code": error_code},
        )
        await self.session.commit()
        return run

    async def request_cancel(self, run_id: str) -> WorkflowRun | None:
        run = await self.session.get(WorkflowRun, run_id)
        if run is None:
            return None
        if run.status in TERMINAL_RUN_STATUSES:
            return run
        run.cancel_requested_at = utc_now()
        if run.status in {"queued", "pending", "planning", "drafting"}:
            run.status = "cancelled"
            run.error = "用户已取消生成"
            self._clear_lease(run)
            await self._append_event_without_commit(
                run_id,
                "workflow_finished",
                {"status": "cancelled"},
            )
        await self.session.commit()
        return run

    async def _run_by_idempotency_key(self, idempotency_key: str) -> WorkflowRun | None:
        return (
            await self.session.execute(
                select(WorkflowRun).where(WorkflowRun.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()

    async def _leased_run(self, run_id: str, worker_id: str) -> WorkflowRun:
        now = utc_now()
        run = (
            await self.session.execute(
                select(WorkflowRun).where(
                    WorkflowRun.id == run_id,
                    WorkflowRun.status == "running",
                    WorkflowRun.lease_owner == worker_id,
                    WorkflowRun.lease_expires_at > now,
                )
            )
        ).scalar_one_or_none()
        if run is None:
            raise LeaseLostError(f"worker {worker_id} no longer owns workflow {run_id}")
        return run

    async def _running_step(
        self,
        run_id: str,
        step_id: str,
        worker_id: str,
    ) -> WorkflowStepRun:
        step = await self.session.get(WorkflowStepRun, step_id)
        if (
            step is None
            or step.workflow_run_id != run_id
            or step.worker_id != worker_id
            or step.status != "running"
        ):
            raise LeaseLostError(f"worker {worker_id} cannot update workflow step {step_id}")
        return step

    async def _append_event_without_commit(
        self,
        run_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> WorkflowEvent:
        run = await self.session.get(WorkflowRun, run_id)
        if run is None:
            raise LookupError(f"workflow run not found: {run_id}")
        sequence_no = run.last_event_sequence + 1
        run.last_event_sequence = sequence_no
        event = WorkflowEvent(
            workflow_run_id=run_id,
            sequence_no=sequence_no,
            event_type=event_type,
            payload_json=payload,
        )
        self.session.add(event)
        projected_event = {
            "event_id": event.sequence_no,
            "run_id": run_id,
            "event": event_type,
            **payload,
        }
        if event_type != "content_delta":
            run.events_json = [*(run.events_json or []), projected_event]
        return event

    @staticmethod
    def _clear_lease(run: WorkflowRun) -> None:
        run.lease_owner = ""
        run.lease_expires_at = None
        run.heartbeat_at = None

    @staticmethod
    def _validate_lease_arguments(worker_id: str, lease_seconds: int) -> None:
        if not worker_id:
            raise ValueError("worker_id is required")
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
