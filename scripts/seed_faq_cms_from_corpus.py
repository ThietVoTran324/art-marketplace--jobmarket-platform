"""Seed faq_articles from app/ai/rag/corpus/*.md (idempotent by slug).

Usage (container, PYTHONPATH=/fastapi):

  python -m scripts.seed_faq_cms_from_corpus
  python -m scripts.seed_faq_cms_from_corpus --status draft
  python -m scripts.seed_faq_cms_from_corpus --dry-run
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from app.ai.rag.reindex import _title_from_markdown, list_faq_files
from app.postgresql.database import SyncSession
from app.postgresql.models import FaqArticlesOrm


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seed FAQ CMS from markdown corpus")
    p.add_argument(
        "--status",
        choices=("draft", "published"),
        default="published",
        help="Status for new/updated rows (default published)",
    )
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    files = list_faq_files()
    if not files:
        print("ERROR: no corpus markdown files", file=sys.stderr)
        return 2

    created = updated = skipped = 0
    with SyncSession() as db:
        for path in files:
            slug = path.stem
            body = path.read_text(encoding="utf-8")
            title = _title_from_markdown(body, slug)[:300]
            row = db.scalar(select(FaqArticlesOrm).where(FaqArticlesOrm.slug == slug))
            if row is None:
                created += 1
                if not args.dry_run:
                    db.add(
                        FaqArticlesOrm(
                            slug=slug,
                            title=title,
                            body=body,
                            status=args.status,
                        )
                    )
                print(f"create {slug}")
                continue
            if row.title == title and row.body == body and row.status == args.status:
                skipped += 1
                print(f"skip {slug}")
                continue
            updated += 1
            print(f"update {slug}")
            if not args.dry_run:
                row.title = title
                row.body = body
                row.status = args.status
                row.updated_at = datetime.now(timezone.utc)
        if not args.dry_run:
            db.commit()

    print(
        f"done created={created} updated={updated} skipped={skipped} "
        f"files={len(files)} dry_run={args.dry_run} status={args.status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
