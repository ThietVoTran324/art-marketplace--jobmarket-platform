"""Share pin + group chat endpoints."""

from __future__ import annotations

import re
import secrets
import string

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, insert, or_, select

from app.api.rest.dependencies import db, filter, user_id
from app.api.rest.sse.routes import active_connections
from app.postgresql.models import (
    ChatMemberOrm,
    ChatOrm,
    MessageOrm,
    PinsOrm,
    SubsrciptionsOrm,
    UsersOrm,
)

from .schemas import (
    CreateGroupIn,
    GroupCreatedOut,
    JoinGroupIn,
    MessageOut,
    SharePinIn,
    ShareTargetOut,
)

router = APIRouter(prefix="/messages", tags=["messages"])

_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_INVITE_ALPHABET = string.ascii_letters + string.digits


def _new_invite_code() -> str:
    return "".join(secrets.choice(_INVITE_ALPHABET) for _ in range(10))


async def _assert_member(db, chat_id: int, uid: int) -> ChatOrm:
    chat = await db.scalar(select(ChatOrm).where(ChatOrm.id == chat_id))
    if chat is None:
        raise HTTPException(status_code=404, detail="chat_not_found")
    member = await db.scalar(
        select(ChatMemberOrm).where(
            ChatMemberOrm.chat_id == chat_id, ChatMemberOrm.user_id == uid
        )
    )
    if member is None and chat.kind == "dm":
        # legacy DM without backfill edge-case
        if chat.user_1_id != uid and chat.user_2_id != uid:
            raise HTTPException(status_code=403, detail="not_a_member")
    elif member is None:
        raise HTTPException(status_code=403, detail="not_a_member")
    return chat


async def _ensure_dm(db, me: int, other: int) -> ChatOrm:
    chat = await db.scalar(
        select(ChatOrm).where(
            ChatOrm.kind == "dm",
            or_(
                and_(ChatOrm.user_1_id == me, ChatOrm.user_2_id == other),
                and_(ChatOrm.user_1_id == other, ChatOrm.user_2_id == me),
            ),
        )
    )
    if chat:
        return chat
    chat = await db.scalar(
        insert(ChatOrm)
        .values(kind="dm", user_1_id=me, user_2_id=other, created_by=me)
        .returning(ChatOrm)
    )
    await db.execute(
        insert(ChatMemberOrm).values(chat_id=chat.id, user_id=me, role="member")
    )
    await db.execute(
        insert(ChatMemberOrm).values(chat_id=chat.id, user_id=other, role="member")
    )
    return chat


async def _collect_share_targets(
    db, user_id: int, q: str | None = None, limit: int = 40
) -> list[ShareTargetOut]:
    qnorm = (q or "").strip().lower()

    dm_chats = await db.scalars(
        select(ChatOrm).where(
            ChatOrm.kind == "dm",
            or_(ChatOrm.user_1_id == user_id, ChatOrm.user_2_id == user_id),
        )
    )
    by_user: dict[int, ShareTargetOut] = {}
    for chat in dm_chats:
        other = chat.user_2_id if chat.user_1_id == user_id else chat.user_1_id
        if other is None:
            continue
        user = await db.scalar(select(UsersOrm).where(UsersOrm.id == other))
        if not user:
            continue
        if qnorm and qnorm not in (user.username or "").lower():
            continue
        by_user[other] = ShareTargetOut(
            user_id=other,
            username=user.username,
            chat_id=chat.id,
            source="chat",
        )

    following_rows = await db.scalars(
        select(UsersOrm)
        .join(SubsrciptionsOrm, SubsrciptionsOrm.following_id == UsersOrm.id)
        .where(SubsrciptionsOrm.follower_id == user_id)
    )
    for user in following_rows:
        if user.id == user_id:
            continue
        if qnorm and qnorm not in (user.username or "").lower():
            continue
        if user.id in by_user:
            continue
        chat = await db.scalar(
            select(ChatOrm).where(
                ChatOrm.kind == "dm",
                or_(
                    and_(ChatOrm.user_1_id == user_id, ChatOrm.user_2_id == user.id),
                    and_(ChatOrm.user_1_id == user.id, ChatOrm.user_2_id == user_id),
                ),
            )
        )
        by_user[user.id] = ShareTargetOut(
            user_id=user.id,
            username=user.username,
            chat_id=chat.id if chat else None,
            source="following",
        )

    out = sorted(by_user.values(), key=lambda x: x.username.lower())
    return out[:limit]


@router.get("/share-targets", response_model=list[ShareTargetOut])
async def list_share_targets(
    db: db,
    user_id: user_id,
    q: str | None = Query(default=None, max_length=80),
    limit: int = Query(40, ge=1, le=100),
):
    """Users from existing DMs + people I follow (not strangers)."""
    return await _collect_share_targets(db, user_id, q, limit)


@router.post("/share-pin", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def share_pin_to_chat(db: db, user_id: user_id, body: SharePinIn):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == body.pin_id))
    if pin is None:
        raise HTTPException(status_code=404, detail="pin_not_found")

    if body.chat_id is not None:
        chat = await _assert_member(db, body.chat_id, user_id)
    elif body.to_user_id is not None:
        if body.to_user_id == user_id:
            raise HTTPException(status_code=400, detail="cannot_share_to_self")
        chat = await _ensure_dm(db, user_id, body.to_user_id)
    else:
        raise HTTPException(status_code=422, detail="chat_id_or_to_user_id_required")

    msg = await db.scalar(
        insert(MessageOrm)
        .values(
            chat_id=chat.id,
            user_id_=user_id,
            content=f"Shared a pin",
            pin_id=body.pin_id,
            message_kind="pin",
            is_read=False,
        )
        .returning(MessageOrm)
    )
    await db.commit()

    # Notify peer via SSE if DM
    peers = await db.scalars(
        select(ChatMemberOrm.user_id).where(
            ChatMemberOrm.chat_id == chat.id, ChatMemberOrm.user_id != user_id
        )
    )
    for peer_id in peers:
        if peer_id in active_connections:
            await active_connections[peer_id].put({"chat_id": chat.id})

    return msg


@router.get("/{chat_id}/media", response_model=list[MessageOut])
async def chat_media_history(db: db, user_id: user_id, chat_id: int, filter: filter):
    await _assert_member(db, chat_id, user_id)
    rows = await db.scalars(
        select(MessageOrm)
        .where(MessageOrm.chat_id == chat_id, MessageOrm.image.is_not(None))
        .order_by(MessageOrm.id.desc())
        .offset(filter.offset)
        .limit(filter.limit)
    )
    return list(rows.all())


@router.get("/{chat_id}/links", response_model=list[MessageOut])
async def chat_link_history(db: db, user_id: user_id, chat_id: int, filter: filter):
    await _assert_member(db, chat_id, user_id)
    # Pull recent text messages and filter URLs in Python (portable)
    rows = await db.scalars(
        select(MessageOrm)
        .where(
            MessageOrm.chat_id == chat_id,
            MessageOrm.content.is_not(None),
            MessageOrm.image.is_(None),
        )
        .order_by(MessageOrm.id.desc())
        .limit(300)
    )
    out: list[MessageOrm] = []
    for m in rows:
        if m.content and _URL_RE.search(m.content):
            out.append(m)
        if len(out) >= filter.limit:
            break
    # apply offset roughly
    return out[filter.offset : filter.offset + filter.limit]


@router.post("/groups", response_model=GroupCreatedOut, status_code=status.HTTP_201_CREATED)
async def create_group(db: db, user_id: user_id, body: CreateGroupIn):
    member_ids = []
    for mid in body.member_ids:
        if mid != user_id and mid not in member_ids:
            member_ids.append(mid)
    if not member_ids:
        raise HTTPException(status_code=422, detail="need_at_least_one_member")

    # Validate members exist and are valid share targets (chat or following)
    targets = {t.user_id for t in await _collect_share_targets(db, user_id, None, 500)}
    for mid in member_ids:
        if mid not in targets:
            raise HTTPException(
                status_code=400, detail=f"user_{mid}_not_in_share_targets"
            )

    code = _new_invite_code()
    # rare collision retry
    for _ in range(5):
        exists = await db.scalar(select(ChatOrm.id).where(ChatOrm.invite_code == code))
        if not exists:
            break
        code = _new_invite_code()

    title = (body.title or "").strip() or None
    chat = await db.scalar(
        insert(ChatOrm)
        .values(
            kind="group",
            title=title,
            invite_code=code,
            created_by=user_id,
            user_1_id=None,
            user_2_id=None,
        )
        .returning(ChatOrm)
    )
    await db.execute(
        insert(ChatMemberOrm).values(chat_id=chat.id, user_id=user_id, role="owner")
    )
    for mid in member_ids:
        await db.execute(
            insert(ChatMemberOrm).values(chat_id=chat.id, user_id=mid, role="member")
        )

    # System-ish first message
    await db.execute(
        insert(MessageOrm).values(
            chat_id=chat.id,
            user_id_=user_id,
            content="Group created",
            message_kind="system",
            is_read=True,
        )
    )
    await db.commit()

    for mid in member_ids:
        if mid in active_connections:
            await active_connections[mid].put({"chat_id": chat.id})

    return GroupCreatedOut(
        id=chat.id, title=chat.title, invite_code=chat.invite_code, kind="group"
    )


@router.post("/groups/join", response_model=GroupCreatedOut)
async def join_group(db: db, user_id: user_id, body: JoinGroupIn):
    code = body.code.strip()
    chat = await db.scalar(
        select(ChatOrm).where(ChatOrm.kind == "group", ChatOrm.invite_code == code)
    )
    if chat is None:
        raise HTTPException(status_code=404, detail="invalid_invite_code")

    existing = await db.scalar(
        select(ChatMemberOrm).where(
            ChatMemberOrm.chat_id == chat.id, ChatMemberOrm.user_id == user_id
        )
    )
    if existing is None:
        await db.execute(
            insert(ChatMemberOrm).values(
                chat_id=chat.id, user_id=user_id, role="member"
            )
        )
        await db.execute(
            insert(MessageOrm).values(
                chat_id=chat.id,
                user_id_=user_id,
                content="Joined the group",
                message_kind="system",
                is_read=True,
            )
        )
        await db.commit()

    return GroupCreatedOut(
        id=chat.id, title=chat.title, invite_code=chat.invite_code or code, kind="group"
    )


@router.get("/groups/{chat_id}/invite-code")
async def get_group_invite_code(db: db, user_id: user_id, chat_id: int):
    chat = await _assert_member(db, chat_id, user_id)
    if chat.kind != "group":
        raise HTTPException(status_code=400, detail="not_a_group")
    return {"invite_code": chat.invite_code, "chat_id": chat.id, "title": chat.title}
