"""Build PinOut with collection image metadata."""
from __future__ import annotations

from sqlalchemy import select

from app.postgresql.models import PinImagesOrm, PinsOrm

from .schemas import PinImageOut, PinOut


async def images_by_pin_ids(db_session, pin_ids: list[int]) -> dict[int, list[PinImageOut]]:
    if not pin_ids:
        return {}
    rows = (
        await db_session.scalars(
            select(PinImagesOrm)
            .where(PinImagesOrm.pin_id.in_(pin_ids))
            .order_by(
                PinImagesOrm.pin_id.asc(),
                PinImagesOrm.sort_order.asc(),
                PinImagesOrm.id.asc(),
            )
        )
    ).all()
    out: dict[int, list[PinImageOut]] = {}
    for row in rows:
        out.setdefault(row.pin_id, []).append(
            PinImageOut(id=row.id, sort_order=row.sort_order)
        )
    return out


async def pin_out(db_session, pin: PinsOrm) -> PinOut:
    mapping = await images_by_pin_ids(db_session, [pin.id])
    pin._pin_images_out = mapping.get(pin.id, [])
    return PinOut.model_validate(pin)


async def pins_out(db_session, pins) -> list[PinOut]:
    pin_list = list(pins)
    mapping = await images_by_pin_ids(db_session, [p.id for p in pin_list])
    result: list[PinOut] = []
    for pin in pin_list:
        pin._pin_images_out = mapping.get(pin.id, [])
        result.append(PinOut.model_validate(pin))
    return result
