"""Orchestrate one chat turn: quota, history window, Gemini + skills, persist; SSE + clear."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import google.generativeai as genai

from app.ai.chat import gemini_chat
from app.ai.chat.skills import collect_cites, dispatch_skill
from app.config import settings
from app.logger import logger
from app.postgresql.models import (
    AiConversationsOrm,
    AiMessagesOrm,
    AiToolInvocationsOrm,
)


OFFTOPIC_HINT = (
    "Mình là trợ lý art / pin / marketplace / job trên web này. "
    "Câu hỏi đó ngoài phạm vi — bạn hỏi về tranh, pin, việc làm hoặc đơn hàng giúp nhé.\n\n"
    "I'm the in-app art & marketplace assistant. "
    "That looks off-topic — ask about art, pins, jobs, or your orders on this site."
)


def _looks_offtopic(text: str) -> bool:
    """Light heuristic only — main boundary is system prompt."""
    t = text.lower().strip()
    if len(t) < 8:
        return False
    product = (
        "pin",
        "tag",
        "job",
        "jd",
        "order",
        "market",
        "sell",
        "buy",
        "apply",
        "ứng tuyển",
        "đơn",
        "tranh",
        "ảnh",
        "art",
        "artist",
        "vẽ",
        "paint",
        "draw",
        "composition",
        "bố cục",
        "màu",
        "color",
        "công ty",
        "company",
        "like",
        "save",
        "listed",
        "rao bán",
        "bán",
    )
    if any(p in t for p in product):
        return False
    hard = (
        "giải phương trình",
        "solve the equation",
        "write me a poem about",
        "viết giúp bài tập",
        "tính đạo hàm",
        "derivative of",
    )
    return any(h in t for h in hard)


def _chunk_text(text: str, size: int = 24) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


async def ensure_conversation(db: AsyncSession, user_id: int) -> AiConversationsOrm:
    row = await db.scalar(
        select(AiConversationsOrm).where(AiConversationsOrm.user_id == user_id)
    )
    if row is not None:
        return row
    row = AiConversationsOrm(user_id=user_id)
    db.add(row)
    await db.flush()
    return row


async def count_user_turns_today(db: AsyncSession, conversation_id: int) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    n = await db.scalar(
        select(func.count())
        .select_from(AiMessagesOrm)
        .where(
            AiMessagesOrm.conversation_id == conversation_id,
            AiMessagesOrm.role == "user",
            AiMessagesOrm.created_at >= start,
        )
    )
    return int(n or 0)


async def load_history_window(
    db: AsyncSession, conversation_id: int, *, limit: int
) -> list[dict[str, str]]:
    rows = (
        await db.scalars(
            select(AiMessagesOrm)
            .where(AiMessagesOrm.conversation_id == conversation_id)
            .order_by(AiMessagesOrm.id.desc())
            .limit(limit)
        )
    ).all()
    rows = list(reversed(rows))
    return [{"role": r.role, "content": r.content} for r in rows]


async def list_messages(
    db: AsyncSession, user_id: int, *, limit: int = 50
) -> list[AiMessagesOrm]:
    conv = await db.scalar(
        select(AiConversationsOrm).where(AiConversationsOrm.user_id == user_id)
    )
    if conv is None:
        return []
    rows = (
        await db.scalars(
            select(AiMessagesOrm)
            .where(AiMessagesOrm.conversation_id == conv.id)
            .order_by(AiMessagesOrm.id.asc())
            .limit(min(limit, 200))
        )
    ).all()
    return list(rows)


async def clear_conversation(db: AsyncSession, user_id: int) -> dict[str, Any]:
    conv = await db.scalar(
        select(AiConversationsOrm).where(AiConversationsOrm.user_id == user_id)
    )
    if conv is None:
        return {"cleared": True, "conversation_id": None, "deleted_messages": 0}

    await db.execute(
        delete(AiToolInvocationsOrm).where(
            AiToolInvocationsOrm.conversation_id == conv.id
        )
    )
    result = await db.execute(
        delete(AiMessagesOrm).where(AiMessagesOrm.conversation_id == conv.id)
    )
    await db.execute(
        update(AiConversationsOrm)
        .where(AiConversationsOrm.id == conv.id)
        .values(updated_at=datetime.now(timezone.utc))
    )
    deleted = int(result.rowcount or 0)
    return {
        "cleared": True,
        "conversation_id": conv.id,
        "deleted_messages": deleted,
    }


async def _begin_turn(
    db: AsyncSession, *, user_id: int, content: str
) -> dict[str, Any]:
    """Validate + persist user message. May return early reply (offtopic / error)."""
    if not settings.AI_CHAT_ENABLED:
        return {"error": "ai_chat_disabled", "status_code": 503}
    if not settings.AI_GEMINI_API_KEY:
        return {"error": "ai_key_missing", "status_code": 503}

    text = (content or "").strip()
    if not text:
        return {"error": "empty_content", "status_code": 400}
    if len(text) > settings.AI_CHAT_MAX_INPUT_CHARS:
        return {"error": "input_too_long", "status_code": 400}

    conv = await ensure_conversation(db, user_id)
    turns_today = await count_user_turns_today(db, conv.id)
    if turns_today >= settings.AI_CHAT_MAX_TURNS_PER_DAY:
        return {"error": "quota_exceeded", "status_code": 429}

    user_msg = AiMessagesOrm(
        conversation_id=conv.id,
        role="user",
        content=text,
        meta={},
    )
    db.add(user_msg)
    await db.flush()

    if _looks_offtopic(text):
        assistant = AiMessagesOrm(
            conversation_id=conv.id,
            role="assistant",
            content=OFFTOPIC_HINT,
            meta={"policy": "offtopic_heuristic"},
        )
        db.add(assistant)
        await db.execute(
            update(AiConversationsOrm)
            .where(AiConversationsOrm.id == conv.id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await db.flush()
        return {
            "early": True,
            "user_message": _msg_out(user_msg),
            "assistant_message": _msg_out(assistant),
            "reply": OFFTOPIC_HINT,
            "cites": [],
        }

    return {
        "early": False,
        "conv": conv,
        "user_msg": user_msg,
        "text": text,
    }


async def _run_model(
    db: AsyncSession,
    *,
    user_id: int,
    conv: AiConversationsOrm,
    user_msg: AiMessagesOrm,
    text: str,
) -> dict[str, Any]:
    history = await load_history_window(
        db, conv.id, limit=settings.AI_CHAT_HISTORY_WINDOW
    )
    gem_history = gemini_chat.history_to_gemini(history[:-1])
    tool_trace: list[dict[str, Any]] = []
    cites: list[dict[str, Any]] = []
    pending_tool_ids: list[int] = []

    try:
        model = gemini_chat.build_model()
        chat = model.start_chat(history=gem_history)
        response = await _to_thread(chat.send_message, text)

        max_steps = 4
        for _ in range(max_steps):
            calls = gemini_chat.extract_function_calls(response)
            if not calls:
                break

            response_parts = []
            for name, args in calls:
                result, status, latency_ms = await dispatch_skill(
                    db, user_id=user_id, tool_name=name, arguments=args or {}
                )
                inv = AiToolInvocationsOrm(
                    conversation_id=conv.id,
                    message_id=None,
                    user_id=user_id,
                    tool_name=name,
                    arguments=args or {},
                    result_summary=result,
                    status=status,
                    latency_ms=latency_ms,
                )
                db.add(inv)
                await db.flush()
                pending_tool_ids.append(inv.id)
                tool_trace.append(
                    {"tool": name, "status": status, "latency_ms": latency_ms}
                )
                if isinstance(result, dict):
                    cites.extend(collect_cites(result))
                response_parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=name,
                            response={"result": result},
                        )
                    )
                )
            response = await _to_thread(
                chat.send_message,
                genai.protos.Content(parts=response_parts),
            )

        reply = gemini_chat.extract_text(response) or (
            "I could not generate a reply. Please try again."
        )
        meta: dict[str, Any] = {}
        if tool_trace:
            meta["tools"] = tool_trace
        if cites:
            meta["cites"] = _dedupe_cites(cites)
        warning = None
    except Exception as exc:
        logger.error("ai chat turn failed user=%s: %s", user_id, exc, exc_info=True)
        if gemini_chat.is_rate_limit_error(exc):
            reply = (
                "AI quota/rate limit reached. Please try again later "
                "(giới hạn API — thử lại sau)."
            )
            meta = {"error": "rate_limit"}
            warning = "rate_limit"
        else:
            reply = (
                "Sorry, the assistant hit an error. Please try again. "
                "(Trợ lý gặp lỗi — thử lại sau.)"
            )
            meta = {"error": "provider", "detail": str(exc)[:200]}
            warning = "provider"

    assistant = AiMessagesOrm(
        conversation_id=conv.id,
        role="assistant",
        content=reply,
        meta=meta,
    )
    db.add(assistant)
    await db.flush()
    if pending_tool_ids:
        await _link_tools_by_ids(db, pending_tool_ids, assistant.id)
    await db.execute(
        update(AiConversationsOrm)
        .where(AiConversationsOrm.id == conv.id)
        .values(updated_at=datetime.now(timezone.utc))
    )

    logger.info(
        "ai_chat_metrics user=%s chars_in=%s chars_out=%s tools=%s",
        user_id,
        len(text),
        len(reply),
        json.dumps(tool_trace),
    )
    out: dict[str, Any] = {
        "user_message": _msg_out(user_msg),
        "assistant_message": _msg_out(assistant),
        "reply": reply,
        "cites": meta.get("cites") or [],
    }
    if warning:
        out["warning"] = warning
    return out


def _dedupe_cites(cites: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, Any]] = set()
    out: list[dict[str, Any]] = []
    for c in cites:
        key = (c.get("type"), c.get("id"), c.get("url"))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


async def run_chat_turn(
    db: AsyncSession,
    *,
    user_id: int,
    content: str,
) -> dict[str, Any]:
    started = await _begin_turn(db, user_id=user_id, content=content)
    if started.get("error"):
        return started
    if started.get("early"):
        return {
            "user_message": started["user_message"],
            "assistant_message": started["assistant_message"],
        }
    return await _run_model(
        db,
        user_id=user_id,
        conv=started["conv"],
        user_msg=started["user_msg"],
        text=started["text"],
    )


async def iter_chat_turn_sse(
    db: AsyncSession,
    *,
    user_id: int,
    content: str,
) -> AsyncIterator[dict[str, Any]]:
    """
    Yield SSE event payloads:
      meta → token* → done | error
    Tool loop finishes before token stream (chunked final reply).
    """
    started = await _begin_turn(db, user_id=user_id, content=content)
    if started.get("error"):
        yield {
            "event": "error",
            "data": {
                "error": started["error"],
                "status_code": started.get("status_code", 400),
            },
        }
        return

    if started.get("early"):
        user_out = started["user_message"]
        asst_out = started["assistant_message"]
        yield {
            "event": "meta",
            "data": {
                "user_message_id": user_out.get("id"),
                "conversation_ready": True,
            },
        }
        for chunk in _chunk_text(started.get("reply") or ""):
            yield {"event": "token", "data": {"text": chunk}}
            await asyncio.sleep(0)
        yield {
            "event": "done",
            "data": {
                "user_message": user_out,
                "assistant_message": asst_out,
                "cites": [],
            },
        }
        return

    yield {
        "event": "meta",
        "data": {
            "user_message_id": started["user_msg"].id,
            "conversation_id": started["conv"].id,
        },
    }

    result = await _run_model(
        db,
        user_id=user_id,
        conv=started["conv"],
        user_msg=started["user_msg"],
        text=started["text"],
    )
    reply = result.get("reply") or ""
    for chunk in _chunk_text(reply):
        yield {"event": "token", "data": {"text": chunk}}
        await asyncio.sleep(0)

    yield {
        "event": "done",
        "data": {
            "user_message": result["user_message"],
            "assistant_message": result["assistant_message"],
            "cites": result.get("cites") or [],
            "warning": result.get("warning"),
        },
    }


async def _link_tools_by_ids(
    db: AsyncSession, tool_ids: list[int], message_id: int
) -> None:
    if not tool_ids:
        return
    await db.execute(
        update(AiToolInvocationsOrm)
        .where(AiToolInvocationsOrm.id.in_(tool_ids))
        .values(message_id=message_id)
    )


def _msg_out(row: AiMessagesOrm) -> dict[str, Any]:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "meta": row.meta if isinstance(row.meta, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def _to_thread(fn, *args):
    return await asyncio.to_thread(fn, *args)
