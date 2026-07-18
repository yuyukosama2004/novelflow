from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid5

CANONICAL_DOCUMENT_SCHEMA = "novelflow.tiptap.v2"
_HASH_SCHEMA = "novelflow.scene-version.v1"
_NODE_ID_NAMESPACE = UUID("1ef77b39-c5b7-4ad4-bb25-9aec860d8f80")
_ADDRESSABLE_NODE_TYPES = frozenset(
    {
        "paragraph",
        "heading",
        "blockquote",
        "codeBlock",
        "bulletList",
        "orderedList",
        "horizontalRule",
        "listItem",
    }
)
_EMPTY_DOCUMENT: dict[str, Any] = {
    "type": "doc",
    "content": [{"type": "paragraph"}],
}
_MARK_WRAPPERS = {
    "code": ("`", "`"),
    "bold": ("**", "**"),
    "italic": ("*", "*"),
    "strike": ("~~", "~~"),
}


class SceneDocumentError(ValueError):
    """Raised when a scene document cannot be normalized without data loss."""


@dataclass(frozen=True)
class SceneDocument:
    content_json: dict[str, Any]
    content_markdown: str
    content_text: str
    schema_version: str
    document_hash: str


def build_scene_document(
    *,
    content_json: dict[str, Any] | None,
    content_markdown: str | None,
) -> SceneDocument:
    """Build a canonical document with Tiptap JSON as the authority."""

    source_document = (
        markdown_to_tiptap(content_markdown or "")
        if content_json is None
        else _normalize_document(content_json)
    )
    document = ensure_scene_node_ids(source_document)
    markdown = tiptap_to_markdown(document)
    submitted_markdown = _normalize_markdown(content_markdown)
    if content_json is not None and submitted_markdown is not None and submitted_markdown != markdown:
        raise SceneDocumentError(
            "content_markdown does not match the canonical Markdown derived from content_json"
        )
    return SceneDocument(
        content_json=document,
        content_markdown=markdown,
        content_text=tiptap_to_plaintext(document),
        schema_version=CANONICAL_DOCUMENT_SCHEMA,
        document_hash=scene_document_hash(document, markdown),
    )


def scene_document_hash(
    content_json: dict[str, Any],
    content_markdown: str,
) -> str:
    """Hash the persisted representation using the original Canon-compatible algorithm."""

    payload = {
        "schema": _HASH_SCHEMA,
        "content_json": content_json,
        "content_markdown": _normalize_line_endings(content_markdown),
    }
    canonical_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def tiptap_to_markdown(value: dict[str, Any]) -> str:
    document = _normalize_document(value)
    return _serialize_blocks(_content(document)).strip()


def tiptap_to_plaintext(value: dict[str, Any]) -> str:
    document = _normalize_document(value)
    return _plaintext_blocks(_content(document)).strip()


def markdown_to_tiptap(value: str) -> dict[str, Any]:
    source = _normalize_line_endings(value).strip()
    if not source:
        return dict(_EMPTY_DOCUMENT)
    if re.search(r"</?[A-Za-z][^>]*>", source):
        raise SceneDocumentError("HTML cannot be imported as canonical Markdown")
    return {
        "type": "doc",
        "content": _parse_markdown_blocks(source.split("\n")),
    }


def ensure_scene_node_ids(value: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with unique stable UUIDs on every addressable block node."""

    document = deepcopy(_normalize_document(value))
    seen: set[str] = set()

    def visit(node: dict[str, Any], path: tuple[int, ...]) -> None:
        if node.get("type") in _ADDRESSABLE_NODE_TYPES:
            attrs = node.get("attrs") or {}
            if not isinstance(attrs, dict):
                raise SceneDocumentError(f"{node.get('type')} attrs must be an object")
            candidate = attrs.get("nodeId")
            node_id = str(candidate) if candidate is not None else ""
            try:
                valid = str(UUID(node_id)) == node_id.lower()
            except (ValueError, AttributeError):
                valid = False
            if not valid or node_id in seen:
                identity_source = json.dumps(
                    {
                        "path": path,
                        "node": _without_node_ids(node),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                node_id = str(uuid5(_NODE_ID_NAMESPACE, identity_source))
            attrs["nodeId"] = node_id
            node["attrs"] = attrs
            seen.add(node_id)
        for index, child in enumerate(_content(node)):
            visit(child, (*path, index))

    visit(document, ())
    return document


def _without_node_ids(value: Any) -> Any:
    if isinstance(value, list):
        return [_without_node_ids(item) for item in value]
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key == "attrs" and isinstance(item, dict):
            attrs = {name: _without_node_ids(attr) for name, attr in item.items() if name != "nodeId"}
            if attrs:
                result[key] = attrs
        else:
            result[key] = _without_node_ids(item)
    return result


def _normalize_document(value: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_json_value(value)
    if not isinstance(normalized, dict) or normalized.get("type") != "doc":
        raise SceneDocumentError("Tiptap document root type must be doc")
    _serialize_blocks(_content(normalized))
    return normalized


def _normalize_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _normalize_line_endings(value)
    if isinstance(value, list):
        return [_normalize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _normalize_json_value(item) for key, item in value.items()}
    raise SceneDocumentError(f"unsupported JSON value: {type(value).__name__}")


def _normalize_line_endings(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _normalize_markdown(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_line_endings(value).strip()


def _content(node: dict[str, Any]) -> list[dict[str, Any]]:
    value = node.get("content", [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SceneDocumentError(f"{node.get('type', 'node')} content must be a list of nodes")
    return value


def _marks(node: dict[str, Any]) -> list[dict[str, Any]]:
    value = node.get("marks", [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SceneDocumentError("text marks must be a list")
    return value


def _escape_markdown(value: str) -> str:
    return re.sub(r"([\\`*_\[\]~])", r"\\\1", value)


def _serialize_inline(nodes: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for node in nodes:
        node_type = node.get("type")
        if node_type == "hardBreak":
            rendered.append("  \n")
            continue
        if node_type != "text":
            raise SceneDocumentError(f"unsupported inline node: {node_type}")
        text_value = node.get("text", "")
        if not isinstance(text_value, str):
            raise SceneDocumentError("text node value must be a string")
        marks = _marks(node)
        has_code = any(mark.get("type") == "code" for mark in marks)
        text = text_value if has_code else _escape_markdown(text_value)
        for mark in marks:
            mark_type = mark.get("type")
            wrapper = _MARK_WRAPPERS.get(str(mark_type))
            if wrapper is None:
                raise SceneDocumentError(f"unsupported text mark: {mark_type}")
            text = f"{wrapper[0]}{text}{wrapper[1]}"
        rendered.append(text)
    return "".join(rendered)


def _serialize_list(node: dict[str, Any], *, ordered: bool) -> str:
    attrs = node.get("attrs") or {}
    if not isinstance(attrs, dict):
        raise SceneDocumentError("list attrs must be an object")
    try:
        start = int(attrs.get("start", 1))
    except (TypeError, ValueError) as exc:
        raise SceneDocumentError("ordered-list start must be an integer") from exc
    items: list[str] = []
    for index, item in enumerate(_content(node)):
        if item.get("type") != "listItem":
            raise SceneDocumentError(f"unsupported list child: {item.get('type')}")
        blocks = _content(item)
        if not blocks or blocks[0].get("type") != "paragraph":
            raise SceneDocumentError("list items must start with a paragraph")
        marker = f"{start + index}. " if ordered else "- "
        lines = [marker + _serialize_inline(_content(blocks[0]))]
        for child in blocks[1:]:
            lines.append("\n".join(f"  {line}" for line in _serialize_block(child).split("\n")))
        items.append("\n".join(lines))
    return "\n".join(items)


def _serialize_block(node: dict[str, Any]) -> str:
    node_type = node.get("type")
    if node_type == "paragraph":
        return _serialize_inline(_content(node))
    if node_type == "heading":
        attrs = node.get("attrs") or {}
        if not isinstance(attrs, dict):
            raise SceneDocumentError("heading attrs must be an object")
        try:
            level = max(1, min(6, int(attrs.get("level", 1))))
        except (TypeError, ValueError) as exc:
            raise SceneDocumentError("heading level must be an integer") from exc
        return f"{'#' * level} {_serialize_inline(_content(node))}"
    if node_type == "blockquote":
        return "\n".join(f"> {line}".rstrip() for line in _serialize_blocks(_content(node)).split("\n"))
    if node_type == "codeBlock":
        attrs = node.get("attrs") or {}
        if not isinstance(attrs, dict):
            raise SceneDocumentError("code-block attrs must be an object")
        language = str(attrs.get("language", ""))
        code_parts: list[str] = []
        for child in _content(node):
            text = child.get("text", "")
            if child.get("type") != "text" or not isinstance(text, str):
                raise SceneDocumentError("code blocks may only contain text nodes")
            code_parts.append(text)
        return f"```{language}\n{''.join(code_parts)}\n```"
    if node_type == "bulletList":
        return _serialize_list(node, ordered=False)
    if node_type == "orderedList":
        return _serialize_list(node, ordered=True)
    if node_type == "horizontalRule":
        return "---"
    raise SceneDocumentError(f"unsupported block node: {node_type}")


def _serialize_blocks(nodes: list[dict[str, Any]]) -> str:
    return "\n\n".join(_serialize_block(node) for node in nodes)


def _inline_plaintext(nodes: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for node in nodes:
        node_type = node.get("type")
        if node_type == "hardBreak":
            rendered.append("\n")
        elif node_type == "text":
            text = node.get("text", "")
            if not isinstance(text, str):
                raise SceneDocumentError("text node value must be a string")
            rendered.append(text)
        else:
            raise SceneDocumentError(f"unsupported inline node: {node_type}")
    return "".join(rendered)


def _plaintext_block(node: dict[str, Any]) -> str:
    node_type = node.get("type")
    if node_type in {"paragraph", "heading"}:
        return _inline_plaintext(_content(node))
    if node_type == "blockquote":
        return _plaintext_blocks(_content(node))
    if node_type == "codeBlock":
        return "".join(str(child.get("text", "")) for child in _content(node))
    if node_type in {"bulletList", "orderedList"}:
        values: list[str] = []
        for item in _content(node):
            if item.get("type") != "listItem":
                raise SceneDocumentError(f"unsupported list child: {item.get('type')}")
            values.append(_plaintext_blocks(_content(item)))
        return "\n".join(values)
    if node_type == "horizontalRule":
        return ""
    raise SceneDocumentError(f"unsupported block node: {node_type}")


def _plaintext_blocks(nodes: list[dict[str, Any]]) -> str:
    return "\n".join(filter(None, (_plaintext_block(node) for node in nodes)))


def _marked(nodes: list[dict[str, Any]], mark_type: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for node in nodes:
        if node.get("type") != "text":
            result.append(node)
            continue
        copied = dict(node)
        copied["marks"] = [*_marks(node), {"type": mark_type}]
        result.append(copied)
    return result


def _parse_inline(value: str) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    plain: list[str] = []
    index = 0

    def flush() -> None:
        if plain:
            nodes.append({"type": "text", "text": "".join(plain)})
            plain.clear()

    candidates = [
        ("**", "**", "bold"),
        ("~~", "~~", "strike"),
        ("`", "`", "code"),
        ("*", "*", "italic"),
        ("_", "_", "italic"),
    ]
    while index < len(value):
        if value[index] == "\\" and index + 1 < len(value):
            plain.append(value[index + 1])
            index += 2
            continue
        active = next(
            (candidate for candidate in candidates if value.startswith(candidate[0], index)),
            None,
        )
        if active is None:
            plain.append(value[index])
            index += 1
            continue
        opening, closing, mark_type = active
        close_index = value.find(closing, index + len(opening))
        if close_index < 0 or close_index == index + len(opening):
            plain.append(opening)
            index += len(opening)
            continue
        flush()
        inner = value[index + len(opening) : close_index]
        children = [{"type": "text", "text": inner}] if mark_type == "code" else _parse_inline(inner)
        nodes.extend(_marked(children, mark_type))
        index = close_index + len(closing)
    flush()
    return nodes


def _parse_paragraph_lines(lines: list[str]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        hard_break = bool(re.search(r" {2,}$", line))
        content.extend(_parse_inline(re.sub(r" {2,}$", "", line)))
        if index < len(lines) - 1:
            content.append({"type": "hardBreak"} if hard_break else {"type": "text", "text": " "})
    return content


def _is_block_start(line: str) -> bool:
    return bool(
        re.match(r"^```", line)
        or re.match(r"^#{1,6}\s+", line)
        or re.match(r"^\s*(?:[-*_]\s*){3,}$", line)
        or re.match(r"^>\s?", line)
        or re.match(r"^\s*[-+*]\s+", line)
        or re.match(r"^\s*\d+\.\s+", line)
    )


def _parse_markdown_blocks(lines: list[str]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        fence = re.match(r"^```([^\s`]*)\s*$", line)
        if fence:
            code: list[str] = []
            index += 1
            while index < len(lines) and not re.match(r"^```\s*$", lines[index]):
                code.append(lines[index])
                index += 1
            if index >= len(lines):
                raise SceneDocumentError("code block is missing a closing fence")
            index += 1
            blocks.append(
                {
                    "type": "codeBlock",
                    "attrs": {"language": fence.group(1)} if fence.group(1) else {},
                    "content": ([{"type": "text", "text": "\n".join(code)}] if code else []),
                }
            )
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            blocks.append(
                {
                    "type": "heading",
                    "attrs": {"level": len(heading.group(1))},
                    "content": _parse_inline(heading.group(2)),
                }
            )
            index += 1
            continue
        if re.match(r"^\s*(?:[-*_]\s*){3,}$", line):
            blocks.append({"type": "horizontalRule"})
            index += 1
            continue
        if re.match(r"^>\s?", line):
            quoted: list[str] = []
            while index < len(lines) and re.match(r"^>\s?", lines[index]):
                quoted.append(re.sub(r"^>\s?", "", lines[index]))
                index += 1
            blocks.append({"type": "blockquote", "content": _parse_markdown_blocks(quoted)})
            continue
        list_match = re.match(r"^\s*(?:(\d+)\.|([-+*]))\s+(.+)$", line)
        if list_match:
            ordered = bool(list_match.group(1))
            start = int(list_match.group(1)) if ordered else 1
            items: list[dict[str, Any]] = []
            while index < len(lines):
                item_match = re.match(
                    r"^\s*(?:(\d+)\.|([-+*]))\s+(.+)$",
                    lines[index],
                )
                if item_match is None or bool(item_match.group(1)) != ordered:
                    break
                items.append(
                    {
                        "type": "listItem",
                        "content": [
                            {
                                "type": "paragraph",
                                "content": _parse_inline(item_match.group(3)),
                            }
                        ],
                    }
                )
                index += 1
            blocks.append(
                {
                    "type": "orderedList" if ordered else "bulletList",
                    "attrs": {"start": start} if ordered else {},
                    "content": items,
                }
            )
            continue
        paragraph = [line]
        index += 1
        while index < len(lines) and lines[index].strip() and not _is_block_start(lines[index]):
            paragraph.append(lines[index])
            index += 1
        blocks.append(
            {
                "type": "paragraph",
                "content": _parse_paragraph_lines(paragraph),
            }
        )
    return blocks
