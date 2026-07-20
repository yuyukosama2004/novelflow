from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any


class ThreeWayMergeConflict(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class _SequenceEdit:
    start: int
    end: int
    replacement: tuple[dict[str, Any], ...]


_MISSING = object()


def merge_block_changes(
    base: dict[str, Any],
    current: dict[str, Any],
    proposed: dict[str, Any],
) -> dict[str, Any]:
    """Merge independent author and proposal edits to one Tiptap block.

    Text is compared as character tokens carrying their marks. Non-text inline
    nodes and nested block nodes remain atomic JSON tokens. Ambiguous overlap is
    rejected instead of guessing an order.
    """

    merged = _merge_mapping(base, current, proposed, path="block")
    current_attrs = current.get("attrs")
    if isinstance(current_attrs, dict) and current_attrs.get("nodeId"):
        attrs = merged.setdefault("attrs", {})
        if not isinstance(attrs, dict):
            raise ThreeWayMergeConflict("THREE_WAY_BLOCK_ATTRIBUTE_CONFLICT")
        attrs["nodeId"] = current_attrs["nodeId"]
    return merged


def _merge_mapping(
    base: dict[str, Any],
    current: dict[str, Any],
    proposed: dict[str, Any],
    *,
    path: str,
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in sorted(base.keys() | current.keys() | proposed.keys()):
        base_value = base.get(key, _MISSING)
        current_value = current.get(key, _MISSING)
        proposed_value = proposed.get(key, _MISSING)
        child_path = f"{path}.{key}"
        value: Any
        if key == "content" and all(
            value is _MISSING or isinstance(value, list)
            for value in (base_value, current_value, proposed_value)
        ):
            value = _merge_content(
                [] if base_value is _MISSING else base_value,
                [] if current_value is _MISSING else current_value,
                [] if proposed_value is _MISSING else proposed_value,
            )
        elif all(
            value is _MISSING or isinstance(value, dict)
            for value in (base_value, current_value, proposed_value)
        ):
            value = _merge_mapping(
                {} if base_value is _MISSING else base_value,
                {} if current_value is _MISSING else current_value,
                {} if proposed_value is _MISSING else proposed_value,
                path=child_path,
            )
        else:
            value = _merge_scalar(
                base_value,
                current_value,
                proposed_value,
                reason=_conflict_reason(child_path),
            )
        if value is not _MISSING:
            merged[key] = value
    return merged


def _merge_scalar(
    base: Any,
    current: Any,
    proposed: Any,
    *,
    reason: str,
) -> Any:
    if current == proposed:
        return deepcopy(current)
    if current == base:
        return deepcopy(proposed)
    if proposed == base:
        return deepcopy(current)
    raise ThreeWayMergeConflict(reason)


def _merge_content(
    base: list[Any],
    current: list[Any],
    proposed: list[Any],
) -> list[dict[str, Any]]:
    base_tokens = _tokenize_content(base)
    current_tokens = _tokenize_content(current)
    proposed_tokens = _tokenize_content(proposed)
    current_edits = _sequence_edits(base_tokens, current_tokens)
    proposed_edits = _sequence_edits(base_tokens, proposed_tokens)
    edits = _combine_edits(current_edits, proposed_edits)
    merged_tokens = _apply_edits(base_tokens, edits)
    return _collapse_tokens(merged_tokens)


def _tokenize_content(content: list[Any]) -> list[dict[str, Any]]:
    tokens: list[dict[str, Any]] = []
    for node in content:
        if not isinstance(node, dict):
            raise ThreeWayMergeConflict("THREE_WAY_BLOCK_STRUCTURE_CONFLICT")
        if node.get("type") == "text" and isinstance(node.get("text"), str):
            text = node["text"]
            shell = {key: deepcopy(value) for key, value in node.items() if key != "text"}
            tokens.extend({**deepcopy(shell), "text": character} for character in text)
        else:
            tokens.append(deepcopy(node))
    return tokens


def _token_key(token: dict[str, Any]) -> str:
    return json.dumps(token, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sequence_edits(
    base: list[dict[str, Any]],
    changed: list[dict[str, Any]],
) -> list[_SequenceEdit]:
    matcher = SequenceMatcher(
        None,
        [_token_key(item) for item in base],
        [_token_key(item) for item in changed],
        autojunk=False,
    )
    return [
        _SequenceEdit(start, end, tuple(deepcopy(changed[changed_start:changed_end])))
        for tag, start, end, changed_start, changed_end in matcher.get_opcodes()
        if tag != "equal"
    ]


def _combine_edits(
    current_edits: list[_SequenceEdit],
    proposed_edits: list[_SequenceEdit],
) -> list[_SequenceEdit]:
    combined = list(current_edits)
    for proposed in proposed_edits:
        duplicate = False
        for current in current_edits:
            if current == proposed:
                duplicate = True
                break
            if _edits_conflict(current, proposed):
                raise ThreeWayMergeConflict("THREE_WAY_BLOCK_CONTENT_CONFLICT")
        if not duplicate:
            combined.append(proposed)
    return sorted(
        combined,
        key=lambda edit: (
            edit.start,
            0 if edit.start == edit.end else 1,
            edit.end,
        ),
    )


def _edits_conflict(left: _SequenceEdit, right: _SequenceEdit) -> bool:
    left_insert = left.start == left.end
    right_insert = right.start == right.end
    if left_insert and right_insert:
        return left.start == right.start and left.replacement != right.replacement
    if left_insert:
        return right.start < left.start < right.end
    if right_insert:
        return left.start < right.start < left.end
    return max(left.start, right.start) < min(left.end, right.end)


def _apply_edits(
    base: list[dict[str, Any]],
    edits: list[_SequenceEdit],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    cursor = 0
    for edit in edits:
        if edit.start < cursor:
            raise ThreeWayMergeConflict("THREE_WAY_BLOCK_CONTENT_CONFLICT")
        output.extend(deepcopy(base[cursor : edit.start]))
        output.extend(deepcopy(edit.replacement))
        cursor = max(cursor, edit.end)
    output.extend(deepcopy(base[cursor:]))
    return output


def _collapse_tokens(tokens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    for token in tokens:
        if token.get("type") != "text":
            collapsed.append(deepcopy(token))
            continue
        shell = {key: value for key, value in token.items() if key != "text"}
        if collapsed and collapsed[-1].get("type") == "text":
            previous_shell = {key: value for key, value in collapsed[-1].items() if key != "text"}
            if previous_shell == shell:
                collapsed[-1]["text"] = str(collapsed[-1].get("text", "")) + str(token.get("text", ""))
                continue
        collapsed.append(deepcopy(token))
    return collapsed


def _conflict_reason(path: str) -> str:
    if path.endswith(".type"):
        return "THREE_WAY_BLOCK_TYPE_CONFLICT"
    if ".attrs" in path:
        return "THREE_WAY_BLOCK_ATTRIBUTE_CONFLICT"
    return "THREE_WAY_BLOCK_STRUCTURE_CONFLICT"
