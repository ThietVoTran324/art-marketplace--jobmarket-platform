"""Skill implementations — authz uses session user_id only (never trust model args for owner)."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.postgresql.models import (
    CompaniesOrm,
    JobApplicationsOrm,
    JobPostsOrm,
    LikesOrm,
    PinListingsOrm,
    PinOrdersOrm,
    PinStatsOrm,
    PinsOrm,
    TagsOrm,
    UsersOrm,
    pins_tags,
    users_pins,
)

ALLOWED_TOOLS = frozenset(
    {
        "search_pins",
        "search_listed_pins",
        "pin_engagement_summary",
        "search_job_posts",
        "my_marketplace_and_jobs_summary",
        "retrieve_knowledge",
        "predict_search_tags",
    }
)


def _frontend_origin() -> str:
    return (settings.FRONTEND_DOMAIN or "").rstrip("/")


def pin_path(pin_id: int) -> str:
    return f"/pin/{pin_id}"


def pin_url(pin_id: int) -> str:
    return f"{_frontend_origin()}{pin_path(pin_id)}"


def pin_thumb_url(pin_id: int) -> str:
    """Cover / first collection image via existing preview endpoint."""
    return f"{_frontend_origin()}/api/pins/upload/{pin_id}"


def user_path(username: str) -> str:
    return f"/user/{username}"


def user_url(username: str) -> str:
    return f"{_frontend_origin()}{user_path(username)}"


def job_path(job_id: int) -> str:
    return f"/jobs/{job_id}"


def job_url(job_id: int) -> str:
    return f"{_frontend_origin()}{job_path(job_id)}"


def _price_label(price_minor: int, currency: str) -> str:
    cur = (currency or "USD").upper()
    if cur == "VND":
        major = price_minor // 100
        return f"{major:,} VND".replace(",", ".")
    return f"{price_minor / 100:.2f} {cur}"


def _clamp_limit(raw: Any, default: int = 5) -> int:
    try:
        return min(max(int(raw or default), 1), 10)
    except (TypeError, ValueError):
        return default


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v or "").strip().lower()
    return s in {"1", "true", "yes", "on"}


async def dispatch_skill(
    db: AsyncSession,
    *,
    user_id: int,
    tool_name: str,
    arguments: dict[str, Any],
) -> tuple[dict[str, Any], str, int]:
    """Run one skill. Returns (result_summary, status, latency_ms)."""
    if tool_name not in ALLOWED_TOOLS:
        return {"error": "tool_not_allowed", "tool": tool_name}, "error", 0

    t0 = time.perf_counter()
    try:
        if tool_name == "search_pins":
            result = await skill_search_pins(db, arguments)
        elif tool_name == "search_listed_pins":
            result = await skill_search_listed_pins(db, arguments)
        elif tool_name == "pin_engagement_summary":
            result = await skill_pin_engagement(db, arguments)
        elif tool_name == "search_job_posts":
            result = await skill_search_jobs(db, arguments)
        elif tool_name == "retrieve_knowledge":
            result = await skill_retrieve_knowledge(db, arguments)
        elif tool_name == "predict_search_tags":
            result = await skill_predict_search_tags(db, arguments)
        else:
            result = await skill_my_activity(db, user_id=user_id, arguments=arguments)
        status = "ok"
    except Exception as exc:  # noqa: BLE001 — surface to model as tool error
        result = {"error": str(exc)[:300]}
        status = "error"
    latency_ms = int((time.perf_counter() - t0) * 1000)
    return result, status, latency_ms


def collect_cites(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten cite-able entities from a skill result for FE meta."""
    cites: list[dict[str, Any]] = []
    for pin in result.get("pins") or []:
        if not isinstance(pin, dict) or pin.get("id") is None:
            continue
        cites.append(
            {
                "type": "pin",
                "id": pin["id"],
                "title": pin.get("title"),
                "url": pin.get("url"),
                "path": pin.get("path"),
                "thumb_url": pin.get("thumb_url"),
            }
        )
    if result.get("pin_id") is not None and result.get("url"):
        cites.append(
            {
                "type": "pin",
                "id": result["pin_id"],
                "title": result.get("title"),
                "url": result.get("url"),
                "path": result.get("path"),
                "thumb_url": result.get("thumb_url"),
            }
        )
    for job in result.get("jobs") or []:
        if not isinstance(job, dict) or job.get("id") is None:
            continue
        cites.append(
            {
                "type": "job",
                "id": job["id"],
                "title": job.get("title"),
                "url": job.get("url"),
                "path": job.get("path"),
                "open_in_new_tab": True,
            }
        )
    for app in result.get("applications") or []:
        if not isinstance(app, dict) or not app.get("url"):
            continue
        cites.append(
            {
                "type": "job",
                "id": app.get("job_post_id"),
                "title": app.get("job_title"),
                "url": app.get("url"),
                "path": app.get("path"),
                "open_in_new_tab": True,
            }
        )
    for order in result.get("orders") or []:
        if not isinstance(order, dict) or not order.get("url"):
            continue
        cites.append(
            {
                "type": "pin",
                "id": order.get("pin_id"),
                "title": f"Order #{order.get('id')}",
                "url": order.get("url"),
                "path": order.get("path"),
                "thumb_url": order.get("thumb_url"),
            }
        )
    for ch in result.get("chunks") or []:
        if not isinstance(ch, dict):
            continue
        st = ch.get("source_type") or "faq"
        raw_path = ch.get("path")
        # Drop corpus filesystem paths; only keep real app routes (/pin/…)
        safe_path = (
            raw_path
            if isinstance(raw_path, str)
            and raw_path.startswith("/")
            and not raw_path.startswith("/null")
            else None
        )
        cites.append(
            {
                "type": "pin" if st == "pin" else "faq",
                "id": ch.get("pin_id") or ch.get("chunk_id") or ch.get("source_key"),
                "title": ch.get("cite_label") or ch.get("title") or ch.get("source_ref"),
                "url": ch.get("url") if st == "pin" else None,
                "path": safe_path if st == "pin" else None,
                "thumb_url": ch.get("thumb_url"),
                "source_ref": ch.get("source_ref"),
            }
        )
    for pin in result.get("pins") or []:
        if not isinstance(pin, dict) or pin.get("id") is None:
            continue
        cites.append(
            {
                "type": "pin",
                "id": pin["id"],
                "title": pin.get("title"),
                "url": pin.get("url"),
                "path": pin.get("path"),
                "thumb_url": pin.get("thumb_url"),
            }
        )
    return cites


async def skill_retrieve_knowledge(
    db: AsyncSession, arguments: dict[str, Any]
) -> dict[str, Any]:
    """RAG FAQ and/or pin hybrid retrieve — public only; no private user data."""
    from app.ai.rag.retrieve import retrieve_knowledge

    if not settings.AI_RAG_ENABLED:
        return {"chunks": [], "pins": [], "note": "ai_rag_disabled"}
    query = str(arguments.get("query") or "").strip()
    limit = arguments.get("limit")
    scope = str(arguments.get("scope") or "all").strip().lower()
    matched = arguments.get("matched_tags") or []
    if isinstance(matched, str):
        matched = [matched]
    return await retrieve_knowledge(
        db,
        query=query,
        limit=limit,
        scope=scope,
        matched_tags=[str(t) for t in matched if t],
    )


async def skill_predict_search_tags(
    db: AsyncSession, arguments: dict[str, Any]
) -> dict[str, Any]:
    """
    Intent → English tags → catalog match → optional pin hybrid hits.
    Read-only: never writes pins_tags / never calls auto-tag.
    """
    import asyncio

    from app.ai.rag.intent_tags import match_predicted_to_catalog, predict_tags_from_query
    from app.ai.rag.retrieve import retrieve_knowledge

    if not settings.AI_RAG_ENABLED:
        return {"note": "ai_rag_disabled", "predicted_tags": [], "matched_tags": []}
    if not settings.AI_RAG_INTENT_TAGS_ENABLED:
        return {"note": "ai_rag_intent_tags_disabled", "predicted_tags": [], "matched_tags": []}

    query = str(arguments.get("query") or "").strip()
    if not query:
        return {"note": "empty_query", "predicted_tags": [], "matched_tags": []}

    try:
        predicted = await asyncio.to_thread(predict_tags_from_query, query)
    except Exception as exc:  # noqa: BLE001
        return {
            "note": "intent_failed",
            "error": str(exc)[:200],
            "predicted_tags": [],
            "matched_tags": [],
        }

    matched = await match_predicted_to_catalog(db, predicted.get("predicted_tags") or [])
    matched_names = [m["name"] for m in matched]

    pins: list[dict[str, Any]] = []
    if matched_names or (predicted.get("predicted_tags") or []):
        # Hybrid pin retrieve; tag branch uses matched catalog names
        try:
            retrieved = await retrieve_knowledge(
                db,
                query=query,
                limit=_clamp_limit(arguments.get("limit"), 5),
                scope="pin",
                matched_tags=matched_names,
            )
            pins = retrieved.get("pins") or []
        except Exception as exc:  # noqa: BLE001
            return {
                "reasoning": predicted.get("reasoning"),
                "predicted_tags": predicted.get("predicted_tags") or [],
                "matched_tags": matched,
                "pins": [],
                "note": "retrieve_failed",
                "error": str(exc)[:200],
            }

    return {
        "reasoning": predicted.get("reasoning"),
        "predicted_tags": predicted.get("predicted_tags") or [],
        "matched_tags": matched,
        "pins": pins,
        "note": "ok" if pins or matched else "no_matches",
    }


async def skill_search_pins(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    """Search public pins by title/description/tag (DB index only — no vision)."""
    query = str(arguments.get("query") or "").strip()
    limit = _clamp_limit(arguments.get("limit"))
    listed_only = _truthy(arguments.get("listed_only"))
    if not query:
        return {"pins": [], "note": "empty_query"}

    pattern = f"%{query}%"
    tag_pin_ids = (
        select(pins_tags.c.pin_id)
        .join(TagsOrm, TagsOrm.id == pins_tags.c.tag_id)
        .where(TagsOrm.name.ilike(pattern))
    )
    stmt = (
        select(
            PinsOrm.id,
            PinsOrm.title,
            PinsOrm.description,
            UsersOrm.username,
            PinListingsOrm.price_minor,
            PinListingsOrm.currency,
            PinListingsOrm.status,
        )
        .join(UsersOrm, UsersOrm.id == PinsOrm.user_id)
        .outerjoin(
            PinListingsOrm,
            (PinListingsOrm.pin_id == PinsOrm.id) & (PinListingsOrm.status == "listed"),
        )
        .where(
            or_(
                PinsOrm.title.ilike(pattern),
                PinsOrm.description.ilike(pattern),
                PinsOrm.id.in_(tag_pin_ids),
            )
        )
        .order_by(PinsOrm.id.desc())
        .limit(limit)
    )
    if listed_only:
        stmt = stmt.where(PinListingsOrm.id.is_not(None))

    rows = (await db.execute(stmt)).all()
    pins = []
    for r in rows:
        item: dict[str, Any] = {
            "id": r.id,
            "title": r.title,
            "description": (r.description or "")[:160],
            "author": r.username,
            "path": pin_path(r.id),
            "url": pin_url(r.id),
            "thumb_url": pin_thumb_url(r.id),
            "listed": r.status == "listed",
        }
        if r.username:
            item["author_path"] = user_path(r.username)
            item["author_url"] = user_url(r.username)
        if r.status == "listed" and r.price_minor is not None:
            item["price_minor"] = r.price_minor
            item["currency"] = r.currency
            item["price_label"] = _price_label(r.price_minor, r.currency or "USD")
        pins.append(item)
    return {
        "pins": pins,
        "note": "matched_title_description_or_tag",
        "listed_only": listed_only,
    }


async def skill_search_listed_pins(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    """Pins currently listed for sale; optional artist username / text query."""
    artist = str(arguments.get("artist_username") or "").strip()
    query = str(arguments.get("query") or "").strip()
    limit = _clamp_limit(arguments.get("limit"))

    stmt = (
        select(
            PinsOrm.id,
            PinsOrm.title,
            PinsOrm.description,
            UsersOrm.username,
            PinListingsOrm.price_minor,
            PinListingsOrm.currency,
        )
        .join(PinListingsOrm, PinListingsOrm.pin_id == PinsOrm.id)
        .join(UsersOrm, UsersOrm.id == PinsOrm.user_id)
        .where(PinListingsOrm.status == "listed")
        .order_by(PinListingsOrm.updated_at.desc(), PinsOrm.id.desc())
        .limit(limit)
    )
    if artist:
        stmt = stmt.where(UsersOrm.username.ilike(artist))
    if query:
        pattern = f"%{query}%"
        tag_pin_ids = (
            select(pins_tags.c.pin_id)
            .join(TagsOrm, TagsOrm.id == pins_tags.c.tag_id)
            .where(TagsOrm.name.ilike(pattern))
        )
        stmt = stmt.where(
            or_(
                PinsOrm.title.ilike(pattern),
                PinsOrm.description.ilike(pattern),
                PinsOrm.id.in_(tag_pin_ids),
                UsersOrm.username.ilike(pattern),
            )
        )

    rows = (await db.execute(stmt)).all()
    if not rows:
        note = "no_listed_pins"
        if artist:
            note = "no_listed_pins_for_artist"
        return {"pins": [], "note": note, "artist_username": artist or None}

    pins = []
    for r in rows:
        item: dict[str, Any] = {
            "id": r.id,
            "title": r.title,
            "description": (r.description or "")[:160],
            "author": r.username,
            "listed": True,
            "price_minor": r.price_minor,
            "currency": r.currency,
            "price_label": _price_label(r.price_minor, r.currency or "USD"),
            "path": pin_path(r.id),
            "url": pin_url(r.id),
            "thumb_url": pin_thumb_url(r.id),
        }
        if r.username:
            item["author_path"] = user_path(r.username)
            item["author_url"] = user_url(r.username)
        pins.append(item)
    return {"pins": pins, "note": "listed_pins", "artist_username": artist or None}


async def skill_pin_engagement(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    pin_id = arguments.get("pin_id")
    try:
        pin_id = int(pin_id)
    except (TypeError, ValueError):
        return {"error": "pin_id_required"}

    pin = await db.get(PinsOrm, pin_id)
    if pin is None:
        return {"error": "pin_not_found"}

    author = await db.get(UsersOrm, pin.user_id)
    likes_count = int(
        await db.scalar(
            select(func.count()).select_from(LikesOrm).where(LikesOrm.pin_id == pin_id)
        )
        or 0
    )
    saves_count = int(
        await db.scalar(
            select(func.count()).select_from(users_pins).where(users_pins.c.pin_id == pin_id)
        )
        or 0
    )
    stats = await db.get(PinStatsOrm, pin_id)
    views = int(stats.view_count) if stats is not None else 0

    first_like = (
        await db.execute(
            select(LikesOrm.id, UsersOrm.username)
            .join(UsersOrm, UsersOrm.id == LikesOrm.user_id)
            .where(LikesOrm.pin_id == pin_id)
            .order_by(LikesOrm.id.asc())
            .limit(1)
        )
    ).first()

    out: dict[str, Any] = {
        "pin_id": pin_id,
        "title": pin.title,
        "likes_count": likes_count,
        "saves_count": saves_count,
        "views_count": views,
        "path": pin_path(pin_id),
        "url": pin_url(pin_id),
        "thumb_url": pin_thumb_url(pin_id),
    }
    if author is not None and author.username:
        out["author"] = author.username
        out["author_path"] = user_path(author.username)
        out["author_url"] = user_url(author.username)
    if first_like is not None and first_like.username:
        out["first_liker_username"] = first_like.username
    return out


async def skill_search_jobs(db: AsyncSession, arguments: dict[str, Any]) -> dict[str, Any]:
    query = str(arguments.get("query") or "").strip()
    limit = _clamp_limit(arguments.get("limit"))
    stmt = (
        select(
            JobPostsOrm.id,
            JobPostsOrm.title,
            JobPostsOrm.status,
            CompaniesOrm.display_name,
        )
        .join(CompaniesOrm, CompaniesOrm.id == JobPostsOrm.company_id)
        .where(
            JobPostsOrm.status == "active",
            CompaniesOrm.status == "active",
            CompaniesOrm.deleted_at.is_(None),
        )
        .order_by(JobPostsOrm.id.desc())
        .limit(limit)
    )
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                JobPostsOrm.title.ilike(pattern),
                CompaniesOrm.display_name.ilike(pattern),
            )
        )
    rows = (await db.execute(stmt)).all()
    return {
        "jobs": [
            {
                "id": r.id,
                "title": r.title,
                "company": r.display_name,
                "status": r.status,
                "path": job_path(r.id),
                "url": job_url(r.id),
                "open_in_new_tab": True,
            }
            for r in rows
        ]
    }


async def skill_my_activity(
    db: AsyncSession,
    *,
    user_id: int,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Orders + applications for the session user only (ignore any user_id in args)."""
    _ = arguments
    limit = 5
    orders = (
        await db.execute(
            select(
                PinOrdersOrm.id,
                PinOrdersOrm.pin_id,
                PinOrdersOrm.status,
                PinOrdersOrm.price_minor,
                PinOrdersOrm.currency,
                PinOrdersOrm.created_at,
            )
            .where(PinOrdersOrm.buyer_user_id == user_id)
            .order_by(PinOrdersOrm.id.desc())
            .limit(limit)
        )
    ).all()
    apps = (
        await db.execute(
            select(
                JobApplicationsOrm.id,
                JobApplicationsOrm.job_post_id,
                JobApplicationsOrm.status,
                JobApplicationsOrm.created_at,
                JobPostsOrm.title,
                CompaniesOrm.display_name,
            )
            .join(JobPostsOrm, JobPostsOrm.id == JobApplicationsOrm.job_post_id)
            .join(CompaniesOrm, CompaniesOrm.id == JobPostsOrm.company_id)
            .where(JobApplicationsOrm.applicant_user_id == user_id)
            .order_by(JobApplicationsOrm.id.desc())
            .limit(limit)
        )
    ).all()
    return {
        "orders": [
            {
                "id": o.id,
                "pin_id": o.pin_id,
                "status": o.status,
                "price_minor": o.price_minor,
                "currency": o.currency,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "path": pin_path(o.pin_id),
                "url": pin_url(o.pin_id),
                "thumb_url": pin_thumb_url(o.pin_id),
            }
            for o in orders
        ],
        "applications": [
            {
                "id": a.id,
                "job_post_id": a.job_post_id,
                "job_title": a.title,
                "company": a.display_name,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "path": job_path(a.job_post_id),
                "url": job_url(a.job_post_id),
                "open_in_new_tab": True,
            }
            for a in apps
        ],
    }
