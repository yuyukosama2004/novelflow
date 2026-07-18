from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.changesets.engine import (
    ChangeApplicationError,
    ChangeOperationInput,
    apply_change_operations,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.documents.codec import SceneDocument, build_scene_document
from app.models.changeset import ChangeOperation, ChangeSet
from app.models.manuscript import SceneWorkingDraft
from app.schemas.changeset import ChangeSetApplyRequest, ChangeSetCreate
from app.services.manuscript_service import ManuscriptService


class ChangeSetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.manuscript = ManuscriptService(session)

    async def create(self, scene_id: str, payload: ChangeSetCreate) -> ChangeSet:
        await self.manuscript.get_scene(scene_id)
        base = await self._base_document(
            scene_id,
            payload.base_working_revision,
            payload.base_version_id,
        )
        if (
            payload.expected_base_document_hash is not None
            and payload.expected_base_document_hash != base.document_hash
        ):
            raise ConflictError(
                "change set baseline changed",
                {"reason": "BASE_DOCUMENT_HASH_MISMATCH"},
            )
        sequences = [item.sequence_no for item in payload.operations]
        if len(sequences) != len(set(sequences)):
            raise ValidationAppError(
                "change operation sequence numbers must be unique",
                {"reason": "DUPLICATE_OPERATION_SEQUENCE"},
            )

        change_set = ChangeSet(
            scene_id=scene_id,
            base_working_revision=payload.base_working_revision,
            base_document_hash=base.document_hash,
            base_version_id=payload.base_version_id,
            purpose=payload.purpose,
            workflow_run_id=payload.workflow_run_id,
            summary=payload.summary,
        )
        operations = [
            ChangeOperation(
                id=str(uuid4()),
                change_set=change_set,
                **item.model_dump(),
            )
            for item in payload.operations
        ]
        try:
            preview = apply_change_operations(
                base.content_json,
                base_document_hash=base.document_hash,
                operations=[self._engine_input(item) for item in operations],
            )
        except ChangeApplicationError as exc:
            raise ValidationAppError(
                "change set operation is invalid",
                {"reason": exc.reason},
            ) from exc
        invalid = [item for item in preview.outcomes if item.status != "accepted"]
        if invalid:
            raise ValidationAppError(
                "change set does not apply cleanly to its baseline",
                {
                    "reason": "INVALID_BASE_OPERATION",
                    "operations": [
                        {"id": item.operation_id, "status": item.status, "reason": item.reason}
                        for item in invalid
                    ],
                },
            )
        self.session.add(change_set)
        await self.session.commit()
        return await self.get(change_set.id)

    async def list_for_scene(self, scene_id: str) -> list[ChangeSet]:
        await self.manuscript.get_scene(scene_id)
        result = await self.session.execute(
            select(ChangeSet)
            .options(selectinload(ChangeSet.operations))
            .where(ChangeSet.scene_id == scene_id)
            .order_by(ChangeSet.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, change_set_id: str) -> ChangeSet:
        result = await self.session.execute(
            select(ChangeSet).options(selectinload(ChangeSet.operations)).where(ChangeSet.id == change_set_id)
        )
        change_set = result.scalar_one_or_none()
        if change_set is None:
            raise NotFoundError("change set not found", {"change_set_id": change_set_id})
        return change_set

    async def apply(
        self,
        change_set_id: str,
        payload: ChangeSetApplyRequest,
    ) -> tuple[ChangeSet, SceneWorkingDraft | None]:
        change_set = await self.get(change_set_id)
        if change_set.status in {"accepted", "rejected"}:
            raise ConflictError(
                "change set is already terminal",
                {"reason": "CHANGE_SET_TERMINAL"},
            )
        operation_by_id = {item.id: item for item in change_set.operations}
        requested_ids = payload.accept_operation_ids | payload.reject_operation_ids
        if requested_ids - operation_by_id.keys():
            raise ValidationAppError(
                "unknown change operation",
                {"reason": "CHANGE_OPERATION_NOT_FOUND"},
            )
        if any(operation_by_id[item].status != "pending" for item in requested_ids):
            raise ConflictError(
                "change operation is already resolved",
                {"reason": "CHANGE_OPERATION_ALREADY_RESOLVED"},
            )

        draft = await self.manuscript.get_working_draft(change_set.scene_id)
        current_revision = draft.revision if draft is not None else 0
        if current_revision != payload.expected_draft_revision:
            raise ConflictError(
                "working draft revision conflict",
                {
                    "reason": "DRAFT_REVISION_CONFLICT",
                    "current_revision": current_revision,
                },
            )
        current = await self._current_document(change_set, draft)
        pending = [self._engine_input(item) for item in change_set.operations if item.status == "pending"]
        result = apply_change_operations(
            current.content_json,
            base_document_hash=change_set.base_document_hash,
            operations=pending,
            accepted_operation_ids=payload.accept_operation_ids,
            allow_rebase=current_revision != change_set.base_working_revision,
        )
        outcomes = {item.operation_id: item for item in result.outcomes}
        has_document_change = any(
            outcomes[operation_id].status == "accepted" for operation_id in payload.accept_operation_ids
        )
        next_revision = current_revision + 1 if has_document_change else current_revision
        if has_document_change:
            await self._write_draft(
                change_set.scene_id,
                draft,
                current_revision,
                result.document.content_json,
                result.document.content_markdown,
            )
        for operation_id in payload.reject_operation_ids:
            operation_by_id[operation_id].status = "rejected"
        for operation_id in payload.accept_operation_ids:
            outcome = outcomes[operation_id]
            operation = operation_by_id[operation_id]
            operation.status = outcome.status
            operation.conflict_reason = outcome.reason
            if outcome.status == "accepted":
                operation.accepted_draft_revision = next_revision
        self._update_status(change_set)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise ConflictError(
                "working draft revision conflict",
                {"reason": "DRAFT_REVISION_CONFLICT"},
            ) from None
        persisted_draft = await self.manuscript.get_working_draft(change_set.scene_id)
        return await self.get(change_set.id), persisted_draft

    async def _base_document(
        self,
        scene_id: str,
        revision: int,
        version_id: str | None,
    ) -> SceneDocument:
        draft = await self.manuscript.get_working_draft(scene_id)
        if revision > 0:
            if draft is None or draft.revision != revision:
                raise ConflictError(
                    "working draft revision conflict",
                    {
                        "reason": "DRAFT_REVISION_CONFLICT",
                        "current_revision": draft.revision if draft else 0,
                    },
                )
            return build_scene_document(
                content_json=draft.content_json,
                content_markdown=draft.content_markdown,
            )
        if version_id is not None:
            version = await self.manuscript.get_version(version_id)
            if version.scene_id != scene_id:
                raise ConflictError("version does not belong to scene")
            return build_scene_document(
                content_json=version.content_json,
                content_markdown=version.content_markdown,
            )
        return build_scene_document(content_json=None, content_markdown="")

    async def _current_document(
        self,
        change_set: ChangeSet,
        draft: SceneWorkingDraft | None,
    ) -> SceneDocument:
        if draft is not None:
            return build_scene_document(
                content_json=draft.content_json,
                content_markdown=draft.content_markdown,
            )
        return await self._base_document(
            change_set.scene_id,
            0,
            change_set.base_version_id,
        )

    async def _write_draft(
        self,
        scene_id: str,
        draft: SceneWorkingDraft | None,
        revision: int,
        content_json: dict,
        content_markdown: str,
    ) -> None:
        if draft is None:
            self.session.add(
                SceneWorkingDraft(
                    scene_id=scene_id,
                    revision=1,
                    content_json=content_json,
                    content_markdown=content_markdown,
                )
            )
            return
        result = await self.session.execute(
            update(SceneWorkingDraft)
            .where(
                SceneWorkingDraft.scene_id == scene_id,
                SceneWorkingDraft.revision == revision,
            )
            .values(
                revision=revision + 1,
                content_json=content_json,
                content_markdown=content_markdown,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError(
                "working draft revision conflict",
                {"reason": "DRAFT_REVISION_CONFLICT"},
            )

    @staticmethod
    def _engine_input(operation: ChangeOperation) -> ChangeOperationInput:
        return ChangeOperationInput(
            id=operation.id,
            sequence_no=operation.sequence_no,
            operation_type=operation.operation_type,  # type: ignore[arg-type]
            target_node_id=operation.target_node_id,
            anchor_before_node_id=operation.anchor_before_node_id,
            anchor_after_node_id=operation.anchor_after_node_id,
            original_json=operation.original_json or None,
            proposed_json=operation.proposed_json or None,
            original_hash=operation.original_hash,
        )

    @staticmethod
    def _update_status(change_set: ChangeSet) -> None:
        statuses = {item.status for item in change_set.operations}
        if statuses <= {"accepted", "rejected"} and "pending" not in statuses:
            change_set.status = "accepted" if "accepted" in statuses else "rejected"
        elif statuses & {"conflicted", "orphaned"}:
            change_set.status = "conflicted"
        elif "accepted" in statuses:
            change_set.status = "partially_accepted"
