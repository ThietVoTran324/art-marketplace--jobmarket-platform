"""Reindex AI RAG corpora.

Usage (container, PYTHONPATH=/fastapi):

  python -m scripts.reindex_rag                  # FAQ only (default)
  python -m scripts.reindex_rag --faq
  python -m scripts.reindex_rag --tags
  python -m scripts.reindex_rag --pins --from-id 1 --to-id 500 --limit 100
  python -m scripts.reindex_rag --all --dry-run
"""

from __future__ import annotations

import argparse
import sys

from app.ai.rag.reindex import reindex_faq_corpus, reindex_pins, reindex_tag_embeddings
from app.config import settings
from app.postgresql.database import SyncSession


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Reindex AI RAG FAQ / pins / tag embeds")
    p.add_argument("--faq", action="store_true", help="Reindex FAQ markdown corpus")
    p.add_argument("--pins", action="store_true", help="Reindex pin parent–child chunks")
    p.add_argument("--tags", action="store_true", help="Reindex tag catalog embeddings")
    p.add_argument("--all", action="store_true", help="FAQ + tags + pins")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--from-id", type=int, default=None)
    p.add_argument("--to-id", type=int, default=None)
    p.add_argument("--limit", type=int, default=None, help="Max pins this run")
    args = p.parse_args(argv)

    do_faq = args.faq or args.all or (not args.pins and not args.tags and not args.faq)
    do_pins = args.pins or args.all
    do_tags = args.tags or args.all

    if not settings.AI_GEMINI_API_KEY and not args.dry_run:
        if (settings.AI_RAG_EMBED_PROVIDER or "").lower() == "gemini":
            print("ERROR: AI_GEMINI_API_KEY empty", file=sys.stderr)
            return 1

    db = SyncSession()
    try:
        out: dict = {}
        if do_faq:
            out["faq"] = reindex_faq_corpus(db, dry_run=args.dry_run)
        if do_tags:
            out["tags"] = reindex_tag_embeddings(db, dry_run=args.dry_run)
        if do_pins:
            out["pins"] = reindex_pins(
                db,
                from_id=args.from_id,
                to_id=args.to_id,
                limit=args.limit,
                dry_run=args.dry_run,
            )
        print(out)
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
