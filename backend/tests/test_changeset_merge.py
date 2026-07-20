from __future__ import annotations

import pytest

from app.changesets.merge import ThreeWayMergeConflict, merge_block_changes

NODE_ID = "13a4b02a-4a2e-4a7b-a88e-6e47d6c8184f"


def paragraph(text: str, *, marks: list[dict] | None = None) -> dict:
    text_node: dict = {"type": "text", "text": text}
    if marks is not None:
        text_node["marks"] = marks
    return {
        "type": "paragraph",
        "attrs": {"nodeId": NODE_ID},
        "content": [text_node],
    }


def text(block: dict) -> str:
    return "".join(item.get("text", "") for item in block.get("content", []))


def test_merges_non_overlapping_author_and_proposal_text_edits() -> None:
    base = paragraph("The lantern went dark.")
    current = paragraph("Suddenly, the lantern went dark.")
    proposed = paragraph("The lantern went completely dark.")

    merged = merge_block_changes(base, current, proposed)

    assert text(merged) == "Suddenly, the lantern went completely dark."
    assert merged["attrs"]["nodeId"] == NODE_ID


def test_preserves_independent_rich_text_marks() -> None:
    base = paragraph("alpha beta")
    current = {
        **paragraph("alpha beta"),
        "content": [
            {"type": "text", "text": "alpha", "marks": [{"type": "bold"}]},
            {"type": "text", "text": " beta"},
        ],
    }
    proposed = paragraph("alpha beta!")

    merged = merge_block_changes(base, current, proposed)

    assert merged["content"] == [
        {"type": "text", "text": "alpha", "marks": [{"type": "bold"}]},
        {"type": "text", "text": " beta!"},
    ]


def test_rejects_overlapping_text_edits_and_same_point_insertions() -> None:
    base = paragraph("the old door")

    with pytest.raises(
        ThreeWayMergeConflict,
        match="THREE_WAY_BLOCK_CONTENT_CONFLICT",
    ):
        merge_block_changes(
            base,
            paragraph("the red door"),
            paragraph("the iron door"),
        )

    with pytest.raises(
        ThreeWayMergeConflict,
        match="THREE_WAY_BLOCK_CONTENT_CONFLICT",
    ):
        merge_block_changes(
            paragraph("door"),
            paragraph("red door"),
            paragraph("old door"),
        )


def test_merges_identical_edits_once_and_keeps_current_node_identity() -> None:
    base = paragraph("door")
    current = paragraph("old door")
    proposed = {
        **paragraph("old door"),
        "attrs": {"nodeId": "99999999-9999-4999-8999-999999999999"},
    }

    merged = merge_block_changes(base, current, proposed)

    assert text(merged) == "old door"
    assert merged["attrs"]["nodeId"] == NODE_ID


def test_rejects_conflicting_block_type_or_attribute_changes() -> None:
    base = paragraph("heading")
    current = {**paragraph("heading"), "type": "heading", "attrs": {"nodeId": NODE_ID, "level": 2}}
    proposed = {
        **paragraph("heading"),
        "type": "blockquote",
    }

    with pytest.raises(
        ThreeWayMergeConflict,
        match="THREE_WAY_BLOCK_TYPE_CONFLICT",
    ):
        merge_block_changes(base, current, proposed)
