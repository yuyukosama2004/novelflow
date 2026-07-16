from __future__ import annotations

import hashlib
import json
from typing import Any


def scene_version_content_hash(
    content_json: dict[str, Any],
    content_markdown: str,
) -> str:
    """Hash the normalized, persisted scene-version payload."""

    payload = {
        "schema": "novelflow.scene-version.v1",
        "content_json": content_json,
        "content_markdown": content_markdown.replace("\r\n", "\n").replace("\r", "\n"),
    }
    canonical_bytes = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()
