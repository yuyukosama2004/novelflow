from __future__ import annotations

import pytest

from app.changesets.engine import (
    ChangeApplicationError,
    ChangeOperationInput,
    apply_change_operations,
)
from app.documents.codec import (
    build_scene_document,
    scene_document_hash,
    scene_node_hash,
    tiptap_to_markdown,
)

FIRST_ID = "13a4b02a-4a2e-4a7b-a88e-6e47d6c8184f"
SECOND_ID = "a88489ae-bdbf-4c6d-82f7-9fe9d1847e24"
THIRD_ID = "b4d91124-74cd-41ac-b97a-7f9957753941"


def paragraph(node_id: str | None, text: str) -> dict:
    attrs = {"nodeId": node_id} if node_id else {}
    return {
        "type": "paragraph",
        "attrs": attrs,
        "content": [{"type": "text", "text": text}],
    }


def base_document():
    return build_scene_document(
        content_json={
            "type": "doc",
            "content": [
                paragraph(FIRST_ID, "first"),
                paragraph(SECOND_ID, "second"),
                paragraph(THIRD_ID, "third"),
            ],
        },
        content_markdown=None,
    )


def test_applies_selected_block_operations_in_sequence() -> None:
    base = base_document()
    operations = [
        ChangeOperationInput(
            id="replace",
            sequence_no=1,
            operation_type="replace_block",
            target_node_id=FIRST_ID,
            original_json=paragraph(FIRST_ID, "first"),
            original_hash=scene_node_hash(paragraph(FIRST_ID, "first")),
            proposed_json=paragraph(None, "replaced"),
        ),
        ChangeOperationInput(
            id="delete",
            sequence_no=2,
            operation_type="delete_block",
            target_node_id=SECOND_ID,
            original_hash=scene_node_hash(paragraph(SECOND_ID, "second")),
        ),
        ChangeOperationInput(
            id="insert",
            sequence_no=3,
            operation_type="insert_after",
            anchor_before_node_id=THIRD_ID,
            proposed_json=paragraph(None, "inserted"),
        ),
    ]

    result = apply_change_operations(
        base.content_json,
        base_document_hash=base.document_hash,
        operations=operations,
        accepted_operation_ids={"replace", "insert"},
    )

    assert result.document.content_markdown == "replaced\n\nsecond\n\nthird\n\ninserted"
    assert [outcome.status for outcome in result.outcomes] == [
        "accepted",
        "skipped",
        "accepted",
    ]
    assert [outcome.application_mode for outcome in result.outcomes] == [
        "direct",
        "",
        "direct",
    ]
    blocks = result.document.content_json["content"]
    assert blocks[0]["attrs"]["nodeId"] == FIRST_ID
    assert len({block["attrs"]["nodeId"] for block in blocks}) == 4


def test_changed_target_conflicts_and_missing_target_is_orphaned() -> None:
    base = base_document()
    operations = [
        ChangeOperationInput(
            id="conflict",
            sequence_no=1,
            operation_type="replace_block",
            target_node_id=FIRST_ID,
            original_hash=scene_node_hash(paragraph(FIRST_ID, "different")),
            proposed_json=paragraph(None, "replacement"),
        ),
        ChangeOperationInput(
            id="orphan",
            sequence_no=2,
            operation_type="delete_block",
            target_node_id="4de6cbcf-c915-43c1-8f03-73eeccf15937",
        ),
    ]

    result = apply_change_operations(
        base.content_json,
        base_document_hash=base.document_hash,
        operations=operations,
    )

    assert result.document.content_markdown == base.content_markdown
    assert [(item.status, item.reason) for item in result.outcomes] == [
        ("conflicted", "ORIGINAL_HASH_MISMATCH"),
        ("orphaned", "TARGET_NODE_NOT_FOUND"),
    ]


def test_rebases_unchanged_target_when_working_revision_has_other_edits() -> None:
    base = base_document()
    edited = {
        **base.content_json,
        "content": [
            *base.content_json["content"],
            paragraph("9d4df08a-7a1f-47c1-b750-ad9e46e86fe2", "author edit"),
        ],
    }

    result = apply_change_operations(
        edited,
        base_document_hash=base.document_hash,
        allow_rebase=True,
        operations=[
            ChangeOperationInput(
                id="replace",
                sequence_no=1,
                operation_type="replace_block",
                target_node_id=FIRST_ID,
                original_hash=scene_node_hash(paragraph(FIRST_ID, "first")),
                proposed_json=paragraph(None, "rebased"),
            )
        ],
    )

    assert result.document.content_markdown == "rebased\n\nsecond\n\nthird\n\nauthor edit"
    assert result.outcomes[0].status == "accepted"
    assert result.outcomes[0].application_mode == "rebased"


def test_three_way_merges_non_overlapping_changes_to_same_block() -> None:
    base = base_document()
    edited = {
        **base.content_json,
        "content": [
            paragraph(FIRST_ID, "author: first"),
            *base.content_json["content"][1:],
        ],
    }
    result = apply_change_operations(
        edited,
        base_document_hash=base.document_hash,
        allow_rebase=True,
        operations=[
            ChangeOperationInput(
                id="merge",
                sequence_no=1,
                operation_type="replace_block",
                target_node_id=FIRST_ID,
                original_json=paragraph(FIRST_ID, "first"),
                original_hash=scene_node_hash(paragraph(FIRST_ID, "first")),
                proposed_json=paragraph(None, "first revised"),
            )
        ],
    )

    assert result.document.content_markdown == "author: first revised\n\nsecond\n\nthird"
    assert result.outcomes[0].status == "accepted"
    assert result.outcomes[0].application_mode == "three_way"
    assert result.outcomes[0].changed is True
    assert result.document.content_json["content"][0]["attrs"]["nodeId"] == FIRST_ID


def test_three_way_rejects_overlapping_changes_and_changed_delete() -> None:
    base = base_document()
    edited = {
        **base.content_json,
        "content": [
            paragraph(FIRST_ID, "author replacement"),
            *base.content_json["content"][1:],
        ],
    }
    operations = [
        ChangeOperationInput(
            id="replace",
            sequence_no=1,
            operation_type="replace_block",
            target_node_id=FIRST_ID,
            original_json=paragraph(FIRST_ID, "first"),
            original_hash=scene_node_hash(paragraph(FIRST_ID, "first")),
            proposed_json=paragraph(None, "model replacement"),
        ),
        ChangeOperationInput(
            id="delete",
            sequence_no=2,
            operation_type="delete_block",
            target_node_id=FIRST_ID,
            original_json=paragraph(FIRST_ID, "first"),
            original_hash=scene_node_hash(paragraph(FIRST_ID, "first")),
        ),
    ]

    result = apply_change_operations(
        edited,
        base_document_hash=base.document_hash,
        allow_rebase=True,
        operations=operations,
    )

    assert result.document.content_markdown == "author replacement\n\nsecond\n\nthird"
    assert [(item.status, item.reason) for item in result.outcomes] == [
        ("conflicted", "THREE_WAY_BLOCK_CONTENT_CONFLICT"),
        ("conflicted", "ORIGINAL_HASH_MISMATCH"),
    ]


def test_replace_preserves_target_identity_and_reports_noop() -> None:
    base = base_document()
    proposed = paragraph("99999999-9999-4999-8999-999999999999", "first")
    result = apply_change_operations(
        base.content_json,
        base_document_hash=base.document_hash,
        operations=[
            ChangeOperationInput(
                id="noop",
                sequence_no=1,
                operation_type="replace_block",
                target_node_id=FIRST_ID,
                original_json=paragraph(FIRST_ID, "first"),
                original_hash=scene_node_hash(paragraph(FIRST_ID, "first")),
                proposed_json=proposed,
            )
        ],
    )

    assert result.document.content_json["content"][0]["attrs"]["nodeId"] == FIRST_ID
    assert result.outcomes[0].status == "accepted"
    assert result.outcomes[0].changed is False


def test_rejects_stale_baseline_and_duplicate_target_identity() -> None:
    base = base_document()
    with pytest.raises(ChangeApplicationError, match="BASE_DOCUMENT_HASH_MISMATCH"):
        apply_change_operations(
            base.content_json,
            base_document_hash="0" * 64,
            operations=[],
        )

    duplicate = {
        "type": "doc",
        "content": [
            paragraph(FIRST_ID, "first"),
            paragraph(FIRST_ID, "duplicate"),
        ],
    }
    duplicate_hash = scene_document_hash(duplicate, tiptap_to_markdown(duplicate))
    with pytest.raises(ChangeApplicationError, match="DUPLICATE_TARGET_NODE_ID"):
        apply_change_operations(
            duplicate,
            base_document_hash=duplicate_hash,
            operations=[
                ChangeOperationInput(
                    id="delete",
                    sequence_no=1,
                    operation_type="delete_block",
                    target_node_id=FIRST_ID,
                )
            ],
        )
