"""Split FAQ markdown into section chunks (~200–500 tokens heuristic)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    heading: str | None
    content: str
    chunk_index: int

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_markdown(text: str, *, max_chars: int = 1600, overlap: int = 120) -> list[TextChunk]:
    """
    Split on ## / ### headings. Oversized sections are further split by size with overlap.
    Rough char budget ≈ 200–500 tokens for English/Vietnamese mix.
    """
    text = (text or "").strip()
    if not text:
        return []

    parts: list[tuple[str | None, str]] = []
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        parts.append((None, text))
    else:
        # Preamble before first heading
        if matches[0].start() > 0:
            pre = text[: matches[0].start()].strip()
            if pre:
                parts.append((None, pre))
        for i, m in enumerate(matches):
            heading = m.group(2).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if body:
                parts.append((heading, f"{heading}\n\n{body}"))
            elif heading:
                parts.append((heading, heading))

    out: list[TextChunk] = []
    idx = 0
    for heading, block in parts:
        if len(block) <= max_chars:
            out.append(TextChunk(heading=heading, content=block, chunk_index=idx))
            idx += 1
            continue
        start = 0
        while start < len(block):
            end = min(start + max_chars, len(block))
            piece = block[start:end].strip()
            if piece:
                out.append(TextChunk(heading=heading, content=piece, chunk_index=idx))
                idx += 1
            if end >= len(block):
                break
            start = max(end - overlap, start + 1)
    return out
