"""User notification + privacy preferences helpers."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.postgresql.models import SubsrciptionsOrm, UsersOrm

DEFAULT_NOTIFICATIONS: dict[str, bool] = {
    "likes": True,
    "comments": True,
    "follows": True,
    "messages": True,
    "jobApps": True,
    "companyJobs": True,
    "marketplace": True,
}

DEFAULT_PRIVACY: dict[str, Any] = {
    "profileDiscoverable": True,
    "showSavedBoards": True,
    "allowMessagesFrom": "everyone",  # everyone | followers | none
    "contactLinks": [],  # [{name, value}] custom public contact rows
}


def _normalize_contact_links(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw[:20]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:80]
        value = str(item.get("value") or "").strip()[:400]
        if not name or not value:
            continue
        out.append({"name": name, "value": value})
    return out

ALLOW_MESSAGES_FROM = frozenset({"everyone", "followers", "none"})

# update_type -> notification pref key; None = always deliver
UPDATE_TYPE_PREF_KEY: dict[str, str | None] = {
    "like_pin": "likes",
    "like_comment": "likes",
    "like_reply": "likes",
    "save_pin": "likes",
    "comment_pin": "comments",
    "reply_comment": "comments",
    "follow": "follows",
    "pin_created_for_followers": "follows",
    "job_created_for_company_followers": "companyJobs",
    "job_application_received": "jobApps",
    "job_application_viewed": "jobApps",
    "job_application_rejected": "jobApps",
    "job_application_passed": "jobApps",
    "work_exp_pending": "jobApps",
    "work_exp_approved": "jobApps",
    "work_exp_rejected": "jobApps",
    "recommendations": None,
    "company_suspended": None,
    "company_unsuspended": None,
}


def merge_notifications(raw: dict | None) -> dict[str, bool]:
    base = dict(DEFAULT_NOTIFICATIONS)
    if not isinstance(raw, dict):
        return base
    for key in DEFAULT_NOTIFICATIONS:
        if key in raw:
            base[key] = bool(raw[key])
    return base


def merge_privacy(raw: dict | None) -> dict[str, Any]:
    base = dict(DEFAULT_PRIVACY)
    if not isinstance(raw, dict):
        return base
    if "profileDiscoverable" in raw:
        base["profileDiscoverable"] = bool(raw["profileDiscoverable"])
    if "showSavedBoards" in raw:
        base["showSavedBoards"] = bool(raw["showSavedBoards"])
    if "allowMessagesFrom" in raw and raw["allowMessagesFrom"] in ALLOW_MESSAGES_FROM:
        base["allowMessagesFrom"] = raw["allowMessagesFrom"]
    if "contactLinks" in raw:
        base["contactLinks"] = _normalize_contact_links(raw["contactLinks"])
    return base


def notifications_of(user: UsersOrm | None) -> dict[str, bool]:
    if user is None:
        return dict(DEFAULT_NOTIFICATIONS)
    return merge_notifications(getattr(user, "notification_prefs", None))


def privacy_of(user: UsersOrm | None) -> dict[str, Any]:
    if user is None:
        return dict(DEFAULT_PRIVACY)
    return merge_privacy(getattr(user, "privacy_prefs", None))


def allows_notification_key(user: UsersOrm | None, key: str) -> bool:
    prefs = notifications_of(user)
    return bool(prefs.get(key, True))


def allows_update_type(user: UsersOrm | None, update_type: str) -> bool:
    key = UPDATE_TYPE_PREF_KEY.get(update_type, None)
    if key is None:
        # Unknown or always-on types
        if update_type in UPDATE_TYPE_PREF_KEY:
            return True
        return True
    return allows_notification_key(user, key)


def is_profile_discoverable(user: UsersOrm | None) -> bool:
    return bool(privacy_of(user).get("profileDiscoverable", True))


def shows_saved_boards(user: UsersOrm | None) -> bool:
    return bool(privacy_of(user).get("showSavedBoards", True))


async def assert_can_start_dm(
    db: AsyncSession, *, sender_id: int, recipient: UsersOrm
) -> None:
    """Raise HTTPException if recipient privacy blocks a new DM from sender."""
    from fastapi import HTTPException

    mode = privacy_of(recipient).get("allowMessagesFrom", "everyone")
    if mode == "everyone":
        return
    if mode == "none":
        raise HTTPException(status_code=403, detail="messaging_disabled")
    # followers: sender follows recipient OR recipient follows sender
    linked = await db.scalar(
        select(SubsrciptionsOrm.id).where(
            or_(
                and_(
                    SubsrciptionsOrm.follower_id == sender_id,
                    SubsrciptionsOrm.following_id == recipient.id,
                ),
                and_(
                    SubsrciptionsOrm.follower_id == recipient.id,
                    SubsrciptionsOrm.following_id == sender_id,
                ),
            )
        )
    )
    if not linked:
        raise HTTPException(status_code=403, detail="messaging_followers_only")

