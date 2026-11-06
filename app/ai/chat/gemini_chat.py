"""Gemini chat with native function calling (no LangChain)."""

from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

from app.ai.chat.prompts import CHAT_SYSTEM
from app.config import settings
from app.logger import logger

_TOOL_DECLS = [
    FunctionDeclaration(
        name="search_pins",
        description=(
            "Search public pins by title, description, or tag name "
            "(uses DB tags/index; does not scan images with vision). "
            "Set listed_only=true to restrict to pins currently for sale."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search text"},
                "limit": {"type": "integer", "description": "Max results 1-10"},
                "listed_only": {
                    "type": "boolean",
                    "description": "If true, only return currently listed pins",
                },
            },
            "required": ["query"],
        },
    ),
    FunctionDeclaration(
        name="search_listed_pins",
        description=(
            "Find pins currently listed for sale (public marketplace). "
            "Optional artist_username and/or query. Returns price and absolute urls."
        ),
        parameters={
            "type": "object",
            "properties": {
                "artist_username": {
                    "type": "string",
                    "description": "Exact artist username (case-insensitive)",
                },
                "query": {"type": "string", "description": "Optional text filter"},
                "limit": {"type": "integer", "description": "Max results 1-10"},
            },
            "required": [],
        },
    ),
    FunctionDeclaration(
        name="pin_engagement_summary",
        description="Public engagement for a pin: likes, saves, views, first liker username if any.",
        parameters={
            "type": "object",
            "properties": {
                "pin_id": {"type": "integer", "description": "Pin id"},
            },
            "required": ["pin_id"],
        },
    ),
    FunctionDeclaration(
        name="search_job_posts",
        description=(
            "Search active public job posts by title or company name. "
            "Each job includes an absolute url to open in a new tab."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": [],
        },
    ),
    FunctionDeclaration(
        name="my_marketplace_and_jobs_summary",
        description=(
            "Summarize the current user's recent marketplace orders and job applications. "
            "No user_id argument — backend binds the logged-in user."
        ),
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    FunctionDeclaration(
        name="retrieve_knowledge",
        description=(
            "RAG retrieve for FAQ how-to and/or pin text discovery. "
            "scope=faq|pin|all. Optional matched_tags from predict_search_tags. "
            "Cite FAQ source_ref or pin url/thumb. "
            "Do NOT use for live listed prices/orders — use SQL tools. Never retag."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "User question or search phrase",
                },
                "limit": {"type": "integer", "description": "Max results 1-10"},
                "scope": {
                    "type": "string",
                    "description": "faq | pin | all (default all)",
                },
                "matched_tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Catalog tag names from predict_search_tags",
                },
            },
            "required": ["query"],
        },
    ),
    FunctionDeclaration(
        name="predict_search_tags",
        description=(
            "For vibe/image discovery in any language: map intent to English kebab-case "
            "tags, match platform tag catalog, return matched_tags + candidate pins "
            "(hybrid RRF). Read-only — does NOT write or retag pins. "
            "Prefer this for chill/mood/paraphrase image search; use search_pins for exact title text; "
            "use search_listed_pins for for-sale listings."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "User request in any language",
                },
                "limit": {"type": "integer", "description": "Max pins 1-10"},
            },
            "required": ["query"],
        },
    ),
]


def _configure() -> None:
    if not settings.AI_GEMINI_API_KEY:
        raise RuntimeError("AI_GEMINI_API_KEY is empty")
    genai.configure(api_key=settings.AI_GEMINI_API_KEY)


def build_model():
    _configure()
    return genai.GenerativeModel(
        model_name=settings.AI_CHAT_MODEL or settings.AI_GEMINI_MODEL,
        system_instruction=CHAT_SYSTEM,
        tools=[Tool(function_declarations=_TOOL_DECLS)],
        generation_config=genai.GenerationConfig(
            temperature=0.4,
            max_output_tokens=settings.AI_CHAT_MAX_OUTPUT_TOKENS,
        ),
    )


def history_to_gemini(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Map stored roles to Gemini contents (user/model)."""
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content or role == "system":
            continue
        gem_role = "user" if role == "user" else "model"
        out.append({"role": gem_role, "parts": [content]})
    return out


def extract_text(response) -> str:
    try:
        text = (response.text or "").strip()
        if text:
            return text
    except Exception:
        pass
    parts: list[str] = []
    try:
        for cand in response.candidates or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                t = getattr(part, "text", None)
                if t:
                    parts.append(t)
    except Exception:
        pass
    return "\n".join(parts).strip()


def extract_function_calls(response) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    try:
        for cand in response.candidates or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                fc = getattr(part, "function_call", None)
                if not fc:
                    continue
                name = getattr(fc, "name", None) or ""
                raw_args = getattr(fc, "args", None) or {}
                if hasattr(raw_args, "items"):
                    args = {k: raw_args[k] for k in raw_args}
                elif isinstance(raw_args, dict):
                    args = dict(raw_args)
                else:
                    args = json.loads(str(raw_args) or "{}")
                if name:
                    calls.append((name, args))
    except Exception as exc:
        logger.warning("extract_function_calls failed: %s", exc)
    return calls


def is_rate_limit_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        status = getattr(current, "status_code", None)
        code = getattr(current, "code", None)
        if status == 429 or code == 429 or code == "429":
            return True
        blob = f"{type(current).__name__} {current}".lower()
        if any(
            k in blob
            for k in ("429", "resource_exhausted", "rate limit", "quota", "too many requests")
        ):
            return True
        current = current.__cause__ or current.__context__
    return False
