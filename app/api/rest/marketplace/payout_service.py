"""Execute seller payout against order snapshot (admin-only callers)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.rest.audit import ACTION_SELLER_PAYOUT_MARK, TARGET_PIN_ORDER, write_audit
from app.api.rest.marketplace.payout_providers import (
    PayoutNotConfigured,
    PayoutTransferRequest,
    get_payout_provider,
)
from app.postgresql.models import PinOrdersOrm, PayoutAttemptsOrm


async def _insert_attempt(
    db: AsyncSession,
    *,
    order_id: int,
    provider: str,
    attempt_status: str,
    actor_user_id: int | None,
    error: str | None = None,
) -> None:
    await db.execute(
        insert(PayoutAttemptsOrm).values(
            order_id=order_id,
            provider=provider,
            status=attempt_status,
            error=(error[:500] if error else None),
            actor_user_id=actor_user_id,
        )
    )


async def execute_order_payout(
    db: AsyncSession,
    *,
    order_id: int,
    actor_user_id: int,
    force_fail: bool = False,
    note: str | None = None,
) -> PinOrdersOrm:
    order = await db.get(PinOrdersOrm, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"order_{order.status}"
        )
    if order.payout_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_paid_out")
    if order.payout_status == "processing":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="payout_in_progress")
    if order.payout_status not in ("pending", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"payout_{order.payout_status}",
        )

    amount = order.payout_amount_vnd
    if not amount or amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="payout_amount_missing"
        )
    if not order.payout_account_identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="payout_destination_missing"
        )
    if order.payout_method_type == "bank" and not order.payout_bank_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="payout_bank_code_missing"
        )

    try:
        provider = get_payout_provider()
    except PayoutNotConfigured as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.code
        ) from e

    now = datetime.now(timezone.utc)
    await db.execute(
        update(PinOrdersOrm)
        .where(PinOrdersOrm.id == order_id)
        .values(payout_status="processing", updated_at=now)
    )
    await _insert_attempt(
        db,
        order_id=order_id,
        provider=provider.name,
        attempt_status="started",
        actor_user_id=actor_user_id,
    )
    await db.flush()

    req = PayoutTransferRequest(
        order_id=order.id,
        amount_vnd=int(amount),
        account_identifier=order.payout_account_identifier,
        account_holder=order.payout_account_holder,
        bank_code=order.payout_bank_code,
        bank_name=order.payout_bank_name,
        method_type=order.payout_method_type,
        idempotency_key=f"order-{order.id}",
    )

    try:
        result = provider.transfer(req, force_fail=force_fail)
    except PayoutNotConfigured as e:
        await _insert_attempt(
            db,
            order_id=order_id,
            provider=provider.name,
            attempt_status="failed",
            actor_user_id=actor_user_id,
            error=e.message,
        )
        order = await db.scalar(
            update(PinOrdersOrm)
            .where(PinOrdersOrm.id == order_id)
            .values(payout_status="failed", updated_at=datetime.now(timezone.utc))
            .returning(PinOrdersOrm)
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.code
        ) from e

    if not result.success:
        err = result.error or "transfer_failed"
        await _insert_attempt(
            db,
            order_id=order_id,
            provider=provider.name,
            attempt_status="failed",
            actor_user_id=actor_user_id,
            error=err,
        )
        order = await db.scalar(
            update(PinOrdersOrm)
            .where(PinOrdersOrm.id == order_id)
            .values(
                payout_status="failed",
                payout_note=(note or "").strip() or order.payout_note,
                updated_at=datetime.now(timezone.utc),
            )
            .returning(PinOrdersOrm)
        )
        await write_audit(
            db,
            actor_user_id=actor_user_id,
            action=ACTION_SELLER_PAYOUT_MARK,
            target_type=TARGET_PIN_ORDER,
            target_id=order_id,
            metadata={
                "payout_status": "failed",
                "provider": provider.name,
                "error": err,
            },
        )
        await db.commit()
        return order

    await _insert_attempt(
        db,
        order_id=order_id,
        provider=provider.name,
        attempt_status="success",
        actor_user_id=actor_user_id,
    )
    marked = datetime.now(timezone.utc)
    order = await db.scalar(
        update(PinOrdersOrm)
        .where(PinOrdersOrm.id == order_id)
        .values(
            payout_status="paid",
            payout_marked_at=marked,
            payout_note=(note or "").strip() or None,
            updated_at=marked,
        )
        .returning(PinOrdersOrm)
    )
    await write_audit(
        db,
        actor_user_id=actor_user_id,
        action=ACTION_SELLER_PAYOUT_MARK,
        target_type=TARGET_PIN_ORDER,
        target_id=order_id,
        metadata={
            "payout_status": "paid",
            "provider": provider.name,
            "provider_ref": result.provider_ref,
            "payout_amount_vnd": order.payout_amount_vnd,
            "seller_user_id": order.seller_user_id,
        },
    )
    await db.commit()
    return order


async def mark_payout_paid_manual(
    db: AsyncSession,
    *,
    order_id: int,
    actor_user_id: int,
    note: str | None = None,
) -> PinOrdersOrm:
    """Shortcut: ops already transferred outside the app."""
    order = await db.get(PinOrdersOrm, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    if order.status != "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"order_{order.status}"
        )
    if order.payout_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_paid_out")

    now = datetime.now(timezone.utc)
    await _insert_attempt(
        db,
        order_id=order_id,
        provider="manual",
        attempt_status="success",
        actor_user_id=actor_user_id,
    )
    order = await db.scalar(
        update(PinOrdersOrm)
        .where(PinOrdersOrm.id == order_id)
        .values(
            payout_status="paid",
            payout_marked_at=now,
            payout_note=(note or "").strip() or None,
            updated_at=now,
        )
        .returning(PinOrdersOrm)
    )
    await write_audit(
        db,
        actor_user_id=actor_user_id,
        action=ACTION_SELLER_PAYOUT_MARK,
        target_type=TARGET_PIN_ORDER,
        target_id=order_id,
        metadata={
            "payout_status": "paid",
            "provider": "manual",
            "payout_amount_vnd": order.payout_amount_vnd,
            "seller_user_id": order.seller_user_id,
        },
    )
    await db.commit()
    return order
