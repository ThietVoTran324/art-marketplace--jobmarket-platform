import json

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.ai.chat.service import clear_conversation, iter_chat_turn_sse, list_messages, run_chat_turn
from app.api.rest.ai_chat.schemas import (
    ChatClearOut,
    ChatHistoryOut,
    ChatMessageIn,
    ChatMessageOut,
    ChatTurnOut,
)
from app.api.rest.dependencies import db, user_id
from app.config import settings

router = APIRouter(prefix="/ai/chat", tags=["ai-chat"])


def _sse_pack(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.get("/messages", response_model=ChatHistoryOut)
async def get_chat_history(
    user_id: user_id,
    db: db,
    limit: int = Query(50, ge=1, le=200),
):
    if not settings.AI_CHAT_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai_chat_disabled")
    rows = await list_messages(db, user_id, limit=limit)
    return ChatHistoryOut(
        messages=[
            ChatMessageOut(
                id=r.id,
                role=r.role,
                content=r.content,
                meta=r.meta if isinstance(r.meta, dict) else {},
                created_at=r.created_at,
            )
            for r in rows
        ]
    )


@router.post("/messages", response_model=ChatTurnOut)
async def post_chat_message(body: ChatMessageIn, user_id: user_id, db: db):
    if not settings.AI_CHAT_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai_chat_disabled")

    result = await run_chat_turn(db, user_id=user_id, content=body.content)
    err = result.get("error")
    if err:
        code = int(result.get("status_code") or 400)
        raise HTTPException(status_code=code, detail=err)

    await db.commit()
    return ChatTurnOut(
        user_message=ChatMessageOut(**result["user_message"]),
        assistant_message=ChatMessageOut(**result["assistant_message"]),
        warning=result.get("warning"),
    )


@router.post("/messages/stream")
async def post_chat_message_stream(body: ChatMessageIn, user_id: user_id, db: db):
    if not settings.AI_CHAT_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai_chat_disabled")
    if not settings.AI_CHAT_SSE_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai_chat_sse_disabled")

    async def event_gen():
        try:
            async for evt in iter_chat_turn_sse(db, user_id=user_id, content=body.content):
                event = evt.get("event") or "message"
                data = evt.get("data") or {}
                if event == "error" and data.get("error") and "user_message" not in data:
                    # Persist nothing useful; still end stream with error event
                    yield _sse_pack(event, data)
                    return
                yield _sse_pack(event, data)
                if event in {"done", "error"}:
                    await db.commit()
                    return
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            yield _sse_pack(
                "error",
                {"error": "stream_failed", "detail": str(exc)[:200]},
            )

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/conversation", response_model=ChatClearOut)
async def delete_conversation(user_id: user_id, db: db):
    if not settings.AI_CHAT_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ai_chat_disabled")
    result = await clear_conversation(db, user_id)
    await db.commit()
    return ChatClearOut(**result)
