"""Build parent–child text chunks for a pin (title / description / tags)."""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.rag.chunking import content_sha256


@dataclass
class PinChildChunk:
    chunk_kind: str
    heading: str | None
    content: str
    chunk_index: int

    @property
    def content_hash(self) -> str:
        return content_sha256(f"{self.chunk_kind}:{self.content}")


def build_pin_child_chunks(
    *,
    title: str | None,
    description: str | None,
    tag_names: list[str],
    max_desc_chars: int = 900,
) -> list[PinChildChunk]:
    """
    Parent = pin document. Children:
    - title
    - description (split if long)
    - tags (single chunk of joined names)
    """
    out: list[PinChildChunk] = []
    idx = 0
    t = (title or "").strip()
    if t:
        out.append(
            PinChildChunk(
                chunk_kind="title",
                heading="title",
                content=t,
                chunk_index=idx,
            )
        )
        idx += 1

    desc = (description or "").strip()
    if desc:
        if len(desc) <= max_desc_chars:
            out.append(
                PinChildChunk(
                    chunk_kind="description",
                    heading="description",
                    content=desc,
                    chunk_index=idx,
                )
            )
            idx += 1
        else:
            start = 0
            part = 0
            while start < len(desc):
                end = min(start + max_desc_chars, len(desc))
                piece = desc[start:end].strip()
                if piece:
                    out.append(
                        PinChildChunk(
                            chunk_kind="description",
                            heading=f"description_{part}",
                            content=piece,
                            chunk_index=idx,
                        )
                    )
                    idx += 1
                    part += 1
                if end >= len(desc):
                    break
                start = max(end - 80, start + 1)

    tags = [n.strip() for n in tag_names if n and n.strip()]
    if tags:
        out.append(
            PinChildChunk(
                chunk_kind="tags",
                heading="tags",
                content=", ".join(tags),
                chunk_index=idx,
            )
        )
        idx += 1

    return out


def pin_document_hash(
    *,
    title: str | None,
    description: str | None,
    tag_names: list[str],
) -> str:
    blob = "\n".join(
        [
            (title or "").strip(),
            (description or "").strip(),
            ",".join(sorted(t.strip().lower() for t in tag_names if t)),
        ]
    )
    return content_sha256(blob)
