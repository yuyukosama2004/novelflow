from __future__ import annotations

from typing import Any

from app.documents.codec import scene_document_hash


def scene_version_content_hash(
    content_json: dict[str, Any],
    content_markdown: str,
) -> str:
    """Hash the normalized, persisted scene-version payload."""
    return scene_document_hash(content_json, content_markdown)
