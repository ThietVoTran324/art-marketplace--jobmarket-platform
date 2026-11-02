"""Gemini vision client for structured tag JSON (+ incorrect existing tags)."""

from __future__ import annotations

import io
from pathlib import Path

import google.generativeai as genai
from PIL import Image

from app.ai.prompts import AUTO_TAG_SYSTEM, build_auto_tag_user_message
from app.ai.schemas import ImageTagResult
from app.config import settings
from app.logger import logger

_MAX_EDGE = 1280

_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "tags": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["name"],
            },
        },
        "incorrect_tags": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["tags", "incorrect_tags"],
}


def _configure() -> None:
    if not settings.AI_GEMINI_API_KEY:
        raise RuntimeError("AI_GEMINI_API_KEY is empty")
    genai.configure(api_key=settings.AI_GEMINI_API_KEY)


def _prepare_image_bytes(path: Path) -> tuple[bytes, str]:
    with Image.open(path) as img:
        img = img.convert("RGB")
        w, h = img.size
        longest = max(w, h)
        if longest > _MAX_EDGE:
            scale = _MAX_EDGE / float(longest)
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), "image/jpeg"


def suggest_tags_for_image(
    path: Path,
    *,
    existing_tags: list[str] | None = None,
) -> ImageTagResult:
    """Call Gemini with the image (+ optional existing tags); return ImageTagResult."""
    _configure()
    image_bytes, mime = _prepare_image_bytes(path)
    existing = list(existing_tags or [])

    model = genai.GenerativeModel(
        model_name=settings.AI_GEMINI_MODEL,
        system_instruction=AUTO_TAG_SYSTEM,
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )

    parts = [
        build_auto_tag_user_message(existing),
        {"mime_type": mime, "data": image_bytes},
    ]
    logger.info(
        "gemini auto-tag request model=%s path=%s existing=%s",
        settings.AI_GEMINI_MODEL,
        path,
        len(existing),
    )
    response = model.generate_content(parts)
    raw = (response.text or "").strip()
    if not raw:
        raise RuntimeError("gemini returned empty response")
    return ImageTagResult.model_validate_json(raw)
