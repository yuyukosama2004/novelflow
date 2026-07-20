from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from app.changesets.merge import ThreeWayMergeConflict, merge_block_changes
from app.documents.codec import (
    SceneDocument,
    build_scene_document,
    scene_document_hash,
    scene_node_hash,
    tiptap_to_markdown,
)

OperationType = Literal["insert_before", "insert_after", "replace_block", "delete_block"]
OperationStatus = Literal["accepted", "skipped", "orphaned", "conflicted"]
ApplicationMode = Literal["", "direct", "rebased", "three_way"]


class ChangeApplicationError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ChangeOperationInput:
    id: str
    sequence_no: int
    operation_type: OperationType
    target_node_id: str | None = None
    anchor_before_node_id: str | None = None
    anchor_after_node_id: str | None = None
    original_json: dict[str, Any] | None = None
    proposed_json: dict[str, Any] | None = None
    original_hash: str = ""


@dataclass(frozen=True)
class OperationOutcome:
    operation_id: str
    status: OperationStatus
    reason: str = ""
    application_mode: ApplicationMode = ""
    changed: bool = False


@dataclass(frozen=True)
class ChangeApplicationResult:
    document: SceneDocument
    outcomes: tuple[OperationOutcome, ...]


def apply_change_operations(
    document: dict[str, Any],
    *,
    base_document_hash: str,
    operations: list[ChangeOperationInput],
    accepted_operation_ids: set[str] | None = None,
    allow_rebase: bool = False,
) -> ChangeApplicationResult:
    current = deepcopy(document)
    actual_hash = scene_document_hash(current, tiptap_to_markdown(current))
    baseline_changed = actual_hash != base_document_hash
    if baseline_changed and not allow_rebase:
        raise ChangeApplicationError("BASE_DOCUMENT_HASH_MISMATCH")
    application_mode: ApplicationMode = "rebased" if baseline_changed else "direct"

    selected = accepted_operation_ids
    outcomes: list[OperationOutcome] = []
    for operation in sorted(operations, key=lambda item: (item.sequence_no, item.id)):
        if selected is not None and operation.id not in selected:
            outcomes.append(OperationOutcome(operation.id, "skipped"))
            continue
        outcome = _apply_operation(
            current,
            operation,
            application_mode=application_mode,
            allow_three_way=allow_rebase,
        )
        outcomes.append(outcome)

    return ChangeApplicationResult(
        document=build_scene_document(content_json=current, content_markdown=None),
        outcomes=tuple(outcomes),
    )


def _apply_operation(
    document: dict[str, Any],
    operation: ChangeOperationInput,
    *,
    application_mode: ApplicationMode,
    allow_three_way: bool,
) -> OperationOutcome:
    blocks = document.get("content")
    if not isinstance(blocks, list):
        raise ChangeApplicationError("DOCUMENT_CONTENT_INVALID")

    if operation.operation_type in {"replace_block", "delete_block"}:
        index = _find_top_level_block(blocks, operation.target_node_id)
        if index is None:
            return OperationOutcome(operation.id, "orphaned", "TARGET_NODE_NOT_FOUND")
        target = blocks[index]
        if not isinstance(target, dict):
            raise ChangeApplicationError("DOCUMENT_BLOCK_INVALID")
        hash_changed = bool(operation.original_hash and scene_node_hash(target) != operation.original_hash)
        content_changed = bool(
            operation.original_json is not None
            and scene_node_hash(operation.original_json) != scene_node_hash(target)
        )
        if hash_changed or content_changed:
            if (
                allow_three_way
                and operation.operation_type == "replace_block"
                and operation.original_json is not None
                and operation.proposed_json is not None
            ):
                try:
                    merged = merge_block_changes(
                        operation.original_json,
                        target,
                        operation.proposed_json,
                    )
                except ThreeWayMergeConflict as exc:
                    return OperationOutcome(
                        operation.id,
                        "conflicted",
                        exc.reason,
                    )
                merged_attrs = merged.get("attrs") or {}
                if not isinstance(merged_attrs, dict):
                    raise ChangeApplicationError("PROPOSED_BLOCK_ATTRS_INVALID")
                merged_attrs["nodeId"] = operation.target_node_id
                merged["attrs"] = merged_attrs
                changed = scene_node_hash(target) != scene_node_hash(merged)
                blocks[index] = merged
                return OperationOutcome(
                    operation.id,
                    "accepted",
                    application_mode="three_way",
                    changed=changed,
                )
            reason = "ORIGINAL_HASH_MISMATCH" if hash_changed else "ORIGINAL_CONTENT_MISMATCH"
            return OperationOutcome(operation.id, "conflicted", reason)
        if operation.operation_type == "delete_block":
            blocks.pop(index)
            return OperationOutcome(
                operation.id,
                "accepted",
                application_mode=application_mode,
                changed=True,
            )
        proposed = _proposed_block(operation)
        proposed_attrs = proposed.get("attrs") or {}
        if not isinstance(proposed_attrs, dict):
            raise ChangeApplicationError("PROPOSED_BLOCK_ATTRS_INVALID")
        proposed_attrs["nodeId"] = operation.target_node_id
        proposed["attrs"] = proposed_attrs
        changed = scene_node_hash(target) != scene_node_hash(proposed)
        blocks[index] = proposed
        return OperationOutcome(
            operation.id,
            "accepted",
            application_mode=application_mode,
            changed=changed,
        )

    if operation.operation_type == "insert_before":
        index = _find_top_level_block(blocks, operation.anchor_after_node_id)
        if index is None:
            return OperationOutcome(operation.id, "orphaned", "ANCHOR_NODE_NOT_FOUND")
        blocks.insert(index, _proposed_block(operation))
        return OperationOutcome(
            operation.id,
            "accepted",
            application_mode=application_mode,
            changed=True,
        )

    if operation.operation_type == "insert_after":
        index = _find_top_level_block(blocks, operation.anchor_before_node_id)
        if index is None:
            return OperationOutcome(operation.id, "orphaned", "ANCHOR_NODE_NOT_FOUND")
        blocks.insert(index + 1, _proposed_block(operation))
        return OperationOutcome(
            operation.id,
            "accepted",
            application_mode=application_mode,
            changed=True,
        )

    raise ChangeApplicationError("OPERATION_TYPE_UNSUPPORTED")


def _find_top_level_block(blocks: list[Any], node_id: str | None) -> int | None:
    if not node_id:
        return None
    matches = [
        index
        for index, block in enumerate(blocks)
        if isinstance(block, dict)
        and isinstance(block.get("attrs"), dict)
        and block["attrs"].get("nodeId") == node_id
    ]
    if len(matches) > 1:
        raise ChangeApplicationError("DUPLICATE_TARGET_NODE_ID")
    return matches[0] if matches else None


def _proposed_block(operation: ChangeOperationInput) -> dict[str, Any]:
    proposed = operation.proposed_json
    if not isinstance(proposed, dict) or proposed.get("type") in {None, "doc", "text"}:
        raise ChangeApplicationError("PROPOSED_BLOCK_INVALID")
    return deepcopy(proposed)
