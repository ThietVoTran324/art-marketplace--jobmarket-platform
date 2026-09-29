"""Regenerate pin previews from originals.

Watermark only for pins currently listed for sale; others get a clean preview.

Usage (from container / venv with app on PYTHONPATH):
  python scripts/regenerate_pin_previews.py
"""
from __future__ import annotations

from sqlalchemy import select

from app.celery.tasks import generate_pin_preview
from app.postgresql.database import get_sync_db
from app.postgresql.models import PinsOrm


def main() -> None:
    db = next(get_sync_db())
    try:
        pins = db.scalars(
            select(PinsOrm.id).where(PinsOrm.original_image.is_not(None))
        ).all()
    finally:
        db.close()

    ok = skip = fail = 0
    for pin_id in pins:
        try:
            # watermarked=None → task inspects pin_listings.status
            result = generate_pin_preview.run(pin_id)
            status = (result or {}).get("status")
            if status == "ok":
                ok += 1
            else:
                skip += 1
            print(f"pin_id={pin_id} {result}")
        except Exception as exc:  # noqa: BLE001 — batch continue
            fail += 1
            print(f"pin_id={pin_id} FAIL {exc}")

    print(f"DONE ok={ok} skip={skip} fail={fail} total={len(pins)}")


if __name__ == "__main__":
    main()
