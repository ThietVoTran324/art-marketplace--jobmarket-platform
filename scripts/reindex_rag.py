"""Reindex AI RAG corpora (throttled like backfill_pin_ai_tags).

Usage (container, PYTHONPATH=/fastapi):

  python -m scripts.reindex_rag                  # FAQ only (default)
  python -m scripts.reindex_rag --faq
  python -m scripts.reindex_rag --tags
  python -m scripts.reindex_rag --pins --from-id 1 --to-id 500 --limit 100
  python -m scripts.reindex_rag --pins --from-id 44 --limit 50 \\
      --batch-size 15 --batch-pause-sec 180 --request-pause-sec 2
  python -m scripts.reindex_rag --all --dry-run

Stop on HTTP 429 / RESOURCE_EXHAUSTED — re-run with --from-id = last_pin_id+1.
"""

from __future__ import annotations

import argparse
import sys

from app.ai.rag.reindex import (
    ReindexRateLimited,
    reindex_faq_corpus,
    reindex_pins,
    reindex_tag_embeddings,
)
from app.config import settings
from app.postgresql.database import SyncSession


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Reindex AI RAG FAQ / pins / tag embeds (rate-limited)"
    )
    p.add_argument("--faq", action="store_true", help="Reindex FAQ markdown corpus")
    p.add_argument("--pins", action="store_true", help="Reindex pin parent–child chunks")
    p.add_argument("--tags", action="store_true", help="Reindex tag catalog embeddings")
    p.add_argument("--all", action="store_true", help="FAQ + tags + pins")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--from-id", type=int, default=None, help="Pins: inclusive start id")
    p.add_argument("--to-id", type=int, default=None, help="Pins: inclusive end id")
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help=f"Max items this run (default {settings.AI_RAG_REINDEX_LIMIT})",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Items per batch before pause (default {settings.AI_RAG_REINDEX_BATCH_SIZE})",
    )
    p.add_argument(
        "--batch-pause-sec",
        type=float,
        default=None,
        help=(
            "Sleep seconds after each full batch "
            f"(default {settings.AI_RAG_REINDEX_BATCH_PAUSE_SEC})"
        ),
    )
    p.add_argument(
        "--request-pause-sec",
        type=float,
        default=None,
        help=(
            "Sleep seconds after each embed unit "
            f"(default from AI_RAG_EMBED_RPM or {settings.AI_RAG_REINDEX_REQUEST_PAUSE_SEC})"
        ),
    )
    return p.parse_args(argv)


def _validate(args: argparse.Namespace) -> str | None:
    if args.from_id is not None and args.to_id is not None and args.from_id > args.to_id:
        return "ERROR: --from-id must be <= --to-id"
    if args.limit is not None and args.limit < 1:
        return "ERROR: --limit must be >= 1"
    if args.batch_size is not None and args.batch_size < 1:
        return "ERROR: --batch-size must be >= 1"
    if args.batch_pause_sec is not None and args.batch_pause_sec < 0:
        return "ERROR: --batch-pause-sec must be >= 0"
    if args.request_pause_sec is not None and args.request_pause_sec < 0:
        return "ERROR: --request-pause-sec must be >= 0"
    return None


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    err = _validate(args)
    if err:
        print(err, file=sys.stderr)
        return 2

    do_faq = args.faq or args.all or (not args.pins and not args.tags and not args.faq)
    do_pins = args.pins or args.all
    do_tags = args.tags or args.all

    if not settings.AI_GEMINI_API_KEY and not args.dry_run:
        if (settings.AI_RAG_EMBED_PROVIDER or "").lower() == "gemini":
            print("ERROR: AI_GEMINI_API_KEY empty", file=sys.stderr)
            return 1

    throttle_kw = {
        "limit": args.limit,
        "batch_size": args.batch_size,
        "batch_pause_sec": args.batch_pause_sec,
        "request_pause_sec": args.request_pause_sec,
    }

    db = SyncSession()
    out: dict = {}
    try:
        if do_faq:
            out["faq"] = reindex_faq_corpus(db, dry_run=args.dry_run, **throttle_kw)
        if do_tags:
            out["tags"] = reindex_tag_embeddings(db, dry_run=args.dry_run, **throttle_kw)
        if do_pins:
            out["pins"] = reindex_pins(
                db,
                from_id=args.from_id,
                to_id=args.to_id,
                dry_run=args.dry_run,
                **throttle_kw,
            )
        print(out)
        return 0
    except ReindexRateLimited as exc:
        db.rollback()
        partial = dict(out)
        # Attach the mode that raised (last attempted) via exception stats.
        if do_pins and "pins" not in partial:
            partial["pins"] = exc.stats
        elif do_tags and "tags" not in partial:
            partial["tags"] = exc.stats
        elif do_faq and "faq" not in partial:
            partial["faq"] = exc.stats
        else:
            partial["rate_limited"] = exc.stats
        print(f"PARTIAL rate_limit: {exc}", file=sys.stderr)
        print(partial)
        last = (exc.stats or {}).get("last_pin_id")
        if last is not None:
            print(
                f"Resume pins with: --from-id {int(last) + 1}",
                file=sys.stderr,
            )
        return 3
    except KeyboardInterrupt:
        db.rollback()
        print("\nInterrupted (Ctrl+C)", file=sys.stderr)
        print(out or {"stopped_reason": "interrupted"})
        return 130
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
