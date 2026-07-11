from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    index: int
    start: int
    end: int
    text: str


def split_text_chunks(content: str, max_chars: int = 2400) -> list[TextChunk]:
    """Split full text without gaps while preferring paragraph boundaries."""

    if not content:
        return [TextChunk(index=0, start=0, end=0, text="")]
    chunks: list[TextChunk] = []
    start = 0
    length = len(content)
    while start < length:
        limit = min(start + max_chars, length)
        end = limit
        if limit < length:
            paragraph_break = content.rfind("\n\n", start + max_chars // 2, limit)
            if paragraph_break > start:
                end = paragraph_break + 2
        chunks.append(
            TextChunk(
                index=len(chunks),
                start=start,
                end=end,
                text=content[start:end],
            )
        )
        start = end
    return chunks
