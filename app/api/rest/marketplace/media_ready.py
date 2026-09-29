"""Marketplace Sprint7 — pin media readiness for listing."""
from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, status

from app.config import settings
from app.postgresql.models import PinsOrm


def assert_pin_media_ready(pin: PinsOrm) -> None:
    """Listed pins must have original + watermarked preview + content hash."""
    if not pin.original_image or not pin.image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pin_media_incomplete",
        )
    if not pin.content_sha256:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pin_hash_missing",
        )
    root = Path(settings.MEDIA_PATH)
    original = root / pin.original_image
    preview = root / pin.image
    if not original.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pin_media_incomplete",
        )
    if not preview.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pin_media_incomplete",
        )
