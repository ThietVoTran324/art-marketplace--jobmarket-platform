"""Sync backfill: Gemini auto-tag for an inclusive pin id range (manual daily runs).

Add-only tags + log incorrect existing tags to pin_ai_analyses.incorrect_tags.
Does NOT unlink tags. Does NOT use Celery — runs in-process with rate limits.

Defaults match the free-tier safe plan: ~250 Gemini calls/day, 15 pins / 3 minutes.

Usage (inside fastapi / worker container, cwd /fastapi or PYTHONPATH set):

  python -m scripts.backfill_pin_ai_tags --from-id 1 --to-id 400 --dry-run
  python -m scripts.backfill_pin_ai_tags --from-id 1 --to-id 400
  python -m scripts.backfill_pin_ai_tags --from-id 1 --to-id 400 --force

Stop on HTTP 429 / RESOURCE_EXHAUSTED — re-run next day with a new range.

Run only ONE instance at a time for a given range (no DB claim/lock).
"""

from __future__ import annotations

import argparse
import sys
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.services.auto_tag import run_auto_tag
from app.config import settings
from app.postgresql.database import SyncSession
from app.postgresql.models import PinAiAnalysesOrm, PinsOrm


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Backfill Gemini auto-tag by pin id range")
    p.add_argument("--from-id", type=int, required=True, help="Inclusive start pin id")
    p.add_argument("--to-id", type=int, required=True, help="Inclusive end pin id")
    p.add_argument(
        "--limit",
        type=int,
        default=250,
        help="Max pins processed this run (default 250)",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=15,
        help="Pins per batch before pause (default 15)",
    )
    p.add_argument(
        "--batch-pause-sec",
        type=float,
        default=180.0,
        help="Sleep seconds after each full batch (default 180)",
    )
    p.add_argument(
        "--request-pause-sec",
        type=float,
        default=2.0,
        help="Sleep seconds after each pin attempt (default 2)",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="Process all pins in range, including those with status=done",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="List eligible pin ids only; no Gemini / DB writes",
    )
    return p.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> str | None:
    if args.from_id > args.to_id:
        return "ERROR: --from-id must be <= --to-id"
    if args.limit < 1:
        return "ERROR: --limit must be >= 1"
    if args.batch_size < 1:
        return "ERROR: --batch-size must be >= 1"
    if args.batch_pause_sec < 0 or args.request_pause_sec < 0:
        return "ERROR: pause values must be >= 0"
    return None


def _is_rate_limit(exc: BaseException) -> bool:
    """Best-effort: walk cause/context; prefer status/code 429 when present."""
    current: BaseException | None = exc
    keywords = (
        "resource_exhausted",
        "too many requests",
        "rate limit",
        "quota exceeded",
        "429",
    )
    while current is not None:
        status = getattr(current, "status_code", None)
        code = getattr(current, "code", None)
        if status == 429 or code == 429 or code == "429":
            return True
        name = type(current).__name__.lower()
        if "resource_exhausted" in name:
            return True
        message = str(current).lower()
        if any(k in message for k in keywords):
            return True
        current = current.__cause__ or current.__context__
    return False


def _eligible_ids(
    db: Session,
    *,
    from_id: int,
    to_id: int,
    force: bool,
    limit: int,
) -> list[int]:
    q = select(PinsOrm.id).where(PinsOrm.id >= from_id, PinsOrm.id <= to_id)
    if not force:
        done_subq = select(PinAiAnalysesOrm.pin_id).where(
            PinAiAnalysesOrm.status == "done"
        )
        q = q.where(~PinsOrm.id.in_(done_subq))
    q = q.order_by(PinsOrm.id.asc()).limit(limit)
    return list(db.scalars(q).all())


def _print_summary(
    *,
    prefix: str,
    ok: int,
    skip: int,
    fail: int,
    gemini_ok: int,
    total_eligible: int,
) -> None:
    print(
        f"{prefix} ok={ok} skip={skip} fail={fail} "
        f"gemini_ok={gemini_ok} total_eligible={total_eligible}"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    err = _validate_args(args)
    if err:
        print(err, file=sys.stderr)
        return 2

    if not settings.AI_GEMINI_API_KEY and not args.dry_run:
        print("ERROR: AI_GEMINI_API_KEY is empty", file=sys.stderr)
        return 2

    with SyncSession() as db:
        eligible = _eligible_ids(
            db,
            from_id=args.from_id,
            to_id=args.to_id,
            force=args.force,
            limit=args.limit,
        )

    print(
        f"range={args.from_id}..{args.to_id} eligible={len(eligible)} "
        f"limit={args.limit} force={args.force} dry_run={args.dry_run} "
        f"model={settings.AI_GEMINI_MODEL}"
    )
    if not eligible:
        print("DONE nothing to do")
        return 0

    if args.dry_run:
        print("eligible ids:", ",".join(str(i) for i in eligible))
        return 0

    ok = skip = fail = 0
    gemini_ok = 0
    n = len(eligible)

    try:
        for i, pin_id in enumerate(eligible):
            with SyncSession() as db:
                try:
                    result = run_auto_tag(db, pin_id)
                    if not isinstance(result, dict):
                        raise ValueError(
                            f"Unexpected auto-tag result: {type(result).__name__}"
                        )
                    status = result.get("status")
                    db.commit()
                    if status == "done":
                        ok += 1
                        gemini_ok += 1
                    else:
                        skip += 1
                    print(f"pin_id={pin_id} {result}")
                except Exception as exc:  # noqa: BLE001 — stop on 429, else continue
                    db.rollback()
                    if _is_rate_limit(exc):
                        print(
                            f"pin_id={pin_id} RATE_LIMIT stop: {exc}",
                            file=sys.stderr,
                        )
                        _print_summary(
                            prefix="PARTIAL",
                            ok=ok,
                            skip=skip,
                            fail=fail,
                            gemini_ok=gemini_ok,
                            total_eligible=n,
                        )
                        return 3
                    fail += 1
                    print(f"pin_id={pin_id} FAIL {exc}", file=sys.stderr)

            # No sleep after the last pin
            if i + 1 >= n:
                break
            if args.request_pause_sec > 0:
                time.sleep(args.request_pause_sec)
            # Extra pause after completing a full batch (not after last pin)
            if (i + 1) % args.batch_size == 0 and args.batch_pause_sec > 0:
                print(f"pause {args.batch_pause_sec}s before next batch...")
                time.sleep(args.batch_pause_sec)
    except KeyboardInterrupt:
        print("\nInterrupted (Ctrl+C)", file=sys.stderr)
        _print_summary(
            prefix="PARTIAL",
            ok=ok,
            skip=skip,
            fail=fail,
            gemini_ok=gemini_ok,
            total_eligible=n,
        )
        return 130

    _print_summary(
        prefix="DONE",
        ok=ok,
        skip=skip,
        fail=fail,
        gemini_ok=gemini_ok,
        total_eligible=n,
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
