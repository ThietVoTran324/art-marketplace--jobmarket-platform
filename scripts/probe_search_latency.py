"""Probe Enter-search latency stack (BE only) — run inside fastapi container.

Usage:
  python -m scripts.probe_search_latency --q we
  python -m scripts.probe_search_latency --q western --limit 10 --pin-id 1
"""

from __future__ import annotations

import argparse
import asyncio
import time
from pathlib import Path

from sqlalchemy import func, select

from app.api.rest.pins.pin_out import pins_out
from app.api.rest.pins.search_service import list_pins_for_target, resolve_search_target
from app.config import settings
from app.postgresql.database import async_session_maker
from app.postgresql.models import CommentsOrm, LikesOrm, PinsOrm, UsersOrm


async def _probe(q: str, limit: int, pin_id: int | None) -> dict:
    out: dict = {"q": q, "limit": limit}
    async with async_session_maker() as db:
        t0 = time.perf_counter()
        target = await resolve_search_target(
            db, value=q, tag_id=None, author_id=None
        )
        out["resolve_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        out["target_kind"] = target.get("kind")
        out["tag_ids"] = target.get("tag_ids") or (
            [target["tag_id"]] if target.get("tag_id") else None
        )

        t1 = time.perf_counter()
        pins = await list_pins_for_target(
            db, target=target, offset=0, limit=limit
        )
        out["list_pins_ms"] = round((time.perf_counter() - t1) * 1000, 1)
        out["pin_count"] = len(pins)
        out["pin_ids"] = [p.id for p in pins]

        t2 = time.perf_counter()
        serialized = await pins_out(db, pins)
        out["pins_out_ms"] = round((time.perf_counter() - t2) * 1000, 1)
        out["serialized_count"] = len(serialized)

        # Same shape as /pins/feed-meta (batch)
        ids = [p.id for p in pins]
        t3 = time.perf_counter()
        if ids:
            pin_rows = (
                await db.scalars(select(PinsOrm).where(PinsOrm.id.in_(ids)))
            ).all()
            owner_ids = {p.user_id for p in pin_rows}
            _ = (
                await db.scalars(select(UsersOrm).where(UsersOrm.id.in_(owner_ids)))
            ).all() if owner_ids else []
            _ = (
                await db.execute(
                    select(LikesOrm.pin_id, func.count())
                    .where(LikesOrm.pin_id.in_(ids))
                    .group_by(LikesOrm.pin_id)
                )
            ).all()
            _ = (
                await db.execute(
                    select(CommentsOrm.pin_id, func.count())
                    .where(CommentsOrm.pin_id.in_(ids))
                    .group_by(CommentsOrm.pin_id)
                )
            ).all()
        out["feed_meta_ms"] = round((time.perf_counter() - t3) * 1000, 1)

        # Media path size for first pin / explicit pin (disk read, no HTTP)
        media_pin = None
        if pin_id is not None:
            media_pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
        elif pins:
            media_pin = pins[0]
        if media_pin is not None:
            media_root = Path(settings.MEDIA_PATH)
            rel = media_pin.videoPreview or media_pin.image
            out["media_pin_id"] = media_pin.id
            out["media_rel"] = rel
            if rel:
                path = media_root / rel
                t4 = time.perf_counter()
                exists = path.exists()
                size = path.stat().st_size if exists else 0
                data = path.read_bytes() if exists else b""
                out["media_read_ms"] = round((time.perf_counter() - t4) * 1000, 1)
                out["media_exists"] = exists
                out["media_bytes"] = size
                out["media_read_bytes"] = len(data)
                # Extrapolate first viewport (limit cards, parallel in browser)
                out["media_est_serial_ms_xN"] = round(
                    out["media_read_ms"] * max(1, len(pins)), 1
                )

        out["search_core_ms"] = round(
            out["resolve_ms"] + out["list_pins_ms"] + out["pins_out_ms"], 1
        )
        out["be_stack_ms"] = round(
            out["search_core_ms"] + out["feed_meta_ms"], 1
        )
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Probe pin search latency breakdown")
    p.add_argument("--q", required=True, help="Search query (as user Enter)")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--pin-id", type=int, default=None, help="Optional media probe pin")
    p.add_argument("--runs", type=int, default=2, help="Warm + measure (prints all)")
    args = p.parse_args(argv)

    async def _runs() -> None:
        for i in range(max(1, args.runs)):
            result = await _probe(args.q, args.limit, args.pin_id)
            print(f"run={i + 1} {result}")

    asyncio.run(_runs())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
