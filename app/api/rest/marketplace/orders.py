"""Order + SePay helpers (Sprint4)."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery.tasks import send_email
from app.config import settings
from app.api.rest.role_gates import assert_can_buy_license
from app.postgresql.models import (
    LicenseCertificatesOrm,
    PaymentEventsOrm,
    PinLicenseAccessOrm,
    PinListingsOrm,
    PinOrdersOrm,
    PinsOrm,
    SellerPaymentMethodsOrm,
    UsersOrm,
)


def compute_charge_amount_vnd(price_minor: int, currency: str) -> int:
    if currency == "VND":
        return max(1, price_minor // 100)
    major = price_minor / 100.0
    return max(1, int(round(major * float(settings.MP_USD_TO_VND_RATE))))


def make_payment_code() -> str:
    # SePay default payment-code prefix is DH (Company → cấu trúc mã thanh toán).
    return f"DH{uuid.uuid4().hex[:12].upper()}"


def transfer_content_for(payment_code: str) -> str:
    """Buyer transfer memo. VietinBank+SePay API requires leading SEVQR or pushes never arrive."""
    code = (payment_code or "").strip().upper()
    prefix = (settings.MP_SEPAY_TRANSFER_CONTENT_PREFIX or "").strip()
    if not prefix or not code:
        return code
    if code.startswith(prefix.upper()):
        return code
    return f"{prefix} {code}"


def extract_payment_code_from_content(content: str) -> str:
    """Pull DH… from memo like 'SEVQR DH0B…' or glued 'SEVQRDH0B…'."""
    text = (content or "").upper()
    m = re.search(r"\bDH[A-Z0-9]{6,}\b", text)
    if m:
        return m.group(0)
    m = re.search(r"DH[A-Z0-9]{6,}", text)
    return m.group(0) if m else ""


def sepay_mock_enabled() -> bool:
    return bool(settings.DEV_MODE and settings.MP_SEPAY_MOCK)


def seller_net_to_vnd(seller_net_minor: int | None, currency: str) -> int:
    if seller_net_minor is None:
        return 0
    if currency == "VND":
        return max(0, seller_net_minor // 100)
    major = seller_net_minor / 100.0
    return max(0, int(round(major * float(settings.MP_USD_TO_VND_RATE))))


def build_vietqr_image_url(*, amount_vnd: int, add_info: str) -> str | None:
    acct = (settings.MP_PLATFORM_ACCOUNT_NUMBER or "").strip()
    bank_name = (settings.MP_PLATFORM_BANK_NAME or "").strip()
    bin_code = (settings.MP_PLATFORM_BANK_BIN or "").strip()
    name = (settings.MP_PLATFORM_ACCOUNT_NAME or "").strip()
    if not acct:
        return None
    # Prefer SePay-hosted VietQR (auto-handles bank quirks like VietinBank SEVQR).
    # https://developer.sepay.vn/vi/tien-ich-khac/tao-qr-code
    bank = bank_name or bin_code
    if bank:
        q = (
            f"acc={quote(acct)}"
            f"&bank={quote(bank)}"
            f"&amount={int(amount_vnd)}"
            f"&des={quote(add_info)}"
            f"&template=compact"
        )
        if name:
            q += f"&holder={quote(name)}"
        return f"https://qr.sepay.vn/img?{q}"
    if not bin_code:
        return None
    base = f"https://img.vietqr.io/image/{bin_code}-{acct}-compact2.png"
    q = f"amount={int(amount_vnd)}&addInfo={quote(add_info)}&accountName={quote(name or 'PAYEE')}"
    return f"{base}?{q}"


def payment_instructions_for(order: PinOrdersOrm) -> dict:
    code = order.payment_code
    memo = transfer_content_for(code)
    amount = int(order.charge_amount_vnd)
    bank_name = (settings.MP_PLATFORM_BANK_NAME or "").strip() or None
    account_number = (settings.MP_PLATFORM_ACCOUNT_NUMBER or "").strip() or None
    account_name = (settings.MP_PLATFORM_ACCOUNT_NAME or "").strip() or None
    bank_bin = (settings.MP_PLATFORM_BANK_BIN or "").strip() or None
    vietqr = build_vietqr_image_url(amount_vnd=amount, add_info=memo)
    pay_url = payment_url_for(order)
    lines = [
        f"Chuyển đúng {amount:,} VND".replace(",", "."),
        f"Nội dung chuyển khoản (bắt buộc): {memo}",
    ]
    if bank_name or account_number:
        lines.append(
            "Tài khoản nhận (chủ nền tảng / SePay): "
            f"{bank_name or '—'} · {account_number or '—'} · {account_name or '—'}"
        )
    else:
        lines.append(
            "Chưa cấu hình MP_PLATFORM_ACCOUNT_* — điền STK nhận tiền vào .env để hiện trên UI."
        )
    lines.append("Sau khi SePay xác nhận, license sẽ mở Download original (preview vẫn watermark).")
    return {
        "payment_code": code,
        "charge_amount_vnd": amount,
        "transfer_content": memo,
        "bank_bin": bank_bin,
        "bank_name": bank_name,
        "account_number": account_number,
        "account_name": account_name,
        "vietqr_image_url": vietqr,
        "payment_url": pay_url,
        "instructions": " | ".join(lines),
    }


def payment_url_for(order: PinOrdersOrm) -> str:
    base = (settings.MP_SEPAY_PAYMENT_BASE_URL or "").rstrip("/")
    if base:
        return f"{base}?code={order.payment_code}&amount={order.charge_amount_vnd}"
    vietqr = build_vietqr_image_url(
        amount_vnd=int(order.charge_amount_vnd),
        add_info=transfer_content_for(order.payment_code),
    )
    if vietqr:
        return vietqr
    return (
        f"{settings.FRONTEND_DOMAIN}/pin/{order.pin_id}"
        f"?order={order.id}&code={order.payment_code}&pay=1"
    )


async def snapshot_seller_payout_destination(
    db: AsyncSession, order: PinOrdersOrm
) -> None:
    """Copy seller primary/verified method onto order for manual/ops payout."""
    method = await db.scalar(
        select(SellerPaymentMethodsOrm)
        .where(
            SellerPaymentMethodsOrm.user_id == order.seller_user_id,
            SellerPaymentMethodsOrm.is_active.is_(True),
            SellerPaymentMethodsOrm.verification_status == "verified",
        )
        .order_by(
            SellerPaymentMethodsOrm.is_primary.desc(),
            SellerPaymentMethodsOrm.id.desc(),
        )
        .limit(1)
    )
    payout_vnd = seller_net_to_vnd(order.seller_net_minor, order.currency)
    values: dict = {"payout_amount_vnd": payout_vnd}
    if method is not None:
        values.update(
            {
                "payout_method_type": method.method_type,
                "payout_display_name": method.display_name,
                "payout_account_identifier": method.account_identifier,
                "payout_bank_name": method.bank_name,
                "payout_bank_code": method.bank_code,
                "payout_account_holder": method.account_holder,
            }
        )
    await db.execute(
        update(PinOrdersOrm).where(PinOrdersOrm.id == order.id).values(**values)
    )


def verify_sepay_signature(
    raw_body: bytes, signature: str | None, timestamp: str | None
) -> None:
    secret = settings.MP_SEPAY_WEBHOOK_SECRET
    if not secret:
        # Local smoke only: allow unsigned webhooks when mock+dev.
        if settings.DEV_MODE and settings.MP_SEPAY_MOCK:
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="sepay_webhook_secret_not_configured",
        )
    if not signature or not timestamp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature")
    try:
        ts = int(timestamp)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad_timestamp") from e
    now = int(datetime.now(timezone.utc).timestamp())
    if abs(now - ts) > 300:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="expired_signature")
    expected = "sha256=" + hmac.new(
        secret.encode(), f"{ts}.".encode() + raw_body, hashlib.sha256
    ).hexdigest()
    if not secrets.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_signature")


async def assert_buyer_can_checkout(
    db: AsyncSession, *, buyer_id: int, pin: PinsOrm, listing: PinListingsOrm
) -> UsersOrm:
    await assert_can_buy_license(db, buyer_id)
    buyer = await db.get(UsersOrm, buyer_id)
    if buyer is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    if not buyer.verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="email_not_verified"
        )
    if pin.user_id == buyer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cannot_buy_own_pin")
    if listing.status != "listed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="listing_not_listed")
    owned = await db.scalar(
        select(PinLicenseAccessOrm.id).where(
            PinLicenseAccessOrm.user_id == buyer_id,
            PinLicenseAccessOrm.pin_id == pin.id,
        )
    )
    if owned is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="already_owned")
    return buyer


async def get_open_pending(
    db: AsyncSession, *, buyer_id: int, pin_id: int
) -> PinOrdersOrm | None:
    now = datetime.now(timezone.utc)
    return await db.scalar(
        select(PinOrdersOrm).where(
            PinOrdersOrm.buyer_user_id == buyer_id,
            PinOrdersOrm.pin_id == pin_id,
            PinOrdersOrm.status == "pending",
            PinOrdersOrm.expires_at > now,
        )
    )


async def cancel_open_pendings_for_pin(
    db: AsyncSession, *, pin_id: int, commit: bool = False
) -> int:
    """Invalidate buyer pending bills when listing price/currency changes."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(PinOrdersOrm)
        .where(
            PinOrdersOrm.pin_id == pin_id,
            PinOrdersOrm.status == "pending",
            PinOrdersOrm.expires_at > now,
        )
        .values(status="cancelled", updated_at=now)
    )
    if commit:
        await db.commit()
    return int(result.rowcount or 0)


async def create_or_reuse_order(
    db: AsyncSession, *, buyer_id: int, pin_id: int
) -> PinOrdersOrm:
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")
    listing = await db.scalar(
        select(PinListingsOrm).where(
            PinListingsOrm.pin_id == pin_id, PinListingsOrm.status == "listed"
        )
    )
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing_not_found")

    await assert_buyer_can_checkout(db, buyer_id=buyer_id, pin=pin, listing=listing)

    existing = await get_open_pending(db, buyer_id=buyer_id, pin_id=pin_id)
    if existing is not None:
        same_price = (
            existing.listing_id == listing.id
            and existing.price_minor == listing.price_minor
            and existing.currency == listing.currency
        )
        if same_price:
            return existing
        # Listing changed since bill was opened — drop stale pending, mint fresh code/amount.
        await db.execute(
            update(PinOrdersOrm)
            .where(PinOrdersOrm.id == existing.id, PinOrdersOrm.status == "pending")
            .values(status="cancelled", updated_at=datetime.now(timezone.utc))
        )
        await db.flush()

    ttl = max(1, int(settings.MP_ORDER_PENDING_TTL_MINUTES))
    now = datetime.now(timezone.utc)
    order = await db.scalar(
        pg_insert(PinOrdersOrm)
        .values(
            buyer_user_id=buyer_id,
            seller_user_id=listing.seller_user_id,
            pin_id=pin_id,
            listing_id=listing.id,
            price_minor=listing.price_minor,
            currency=listing.currency,
            charge_amount_vnd=compute_charge_amount_vnd(
                listing.price_minor, listing.currency
            ),
            payment_code=make_payment_code(),
            provider="sepay",
            status="pending",
            payout_status="pending",
            expires_at=now + timedelta(minutes=ttl),
        )
        .returning(PinOrdersOrm)
    )
    await db.commit()
    return order


async def mark_order_paid(
    db: AsyncSession,
    order: PinOrdersOrm,
    *,
    provider_event_id: str,
    payload: dict,
) -> PinOrdersOrm:
    """Idempotent paid + grant. Caller must commit."""
    # Dedup event first
    inserted = await db.execute(
        pg_insert(PaymentEventsOrm)
        .values(
            provider="sepay",
            provider_event_id=str(provider_event_id),
            order_id=order.id,
            payload=payload,
        )
        .on_conflict_do_nothing(
            constraint="uq_payment_events_provider_event"
        )
        .returning(PaymentEventsOrm.id)
    )
    event_id = inserted.scalar_one_or_none()
    if event_id is None:
        # duplicate webhook — reload order
        return await db.get(PinOrdersOrm, order.id)

    if order.status == "paid":
        return order
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"order_{order.status}"
        )

    order_id = order.id
    pct = max(0.0, min(100.0, float(settings.MP_PLATFORM_COMMISSION_PERCENT)))
    commission_minor = int(round(order.price_minor * pct / 100.0))
    seller_net = order.price_minor - commission_minor
    now = datetime.now(timezone.utc)

    updated = await db.scalar(
        update(PinOrdersOrm)
        .where(PinOrdersOrm.id == order_id, PinOrdersOrm.status == "pending")
        .values(
            status="paid",
            paid_at=now,
            commission_percent=pct,
            commission_minor=commission_minor,
            seller_net_minor=seller_net,
            payout_status="pending",
            updated_at=now,
        )
        .returning(PinOrdersOrm)
    )
    if updated is None:
        return await db.get(PinOrdersOrm, order_id)

    order = updated
    await snapshot_seller_payout_destination(db, order)

    await db.execute(
        pg_insert(PinLicenseAccessOrm)
        .values(
            user_id=order.buyer_user_id,
            pin_id=order.pin_id,
            order_id=order.id,
        )
        .on_conflict_do_nothing(constraint="uq_pin_license_access_user_pin")
    )

    pin = await db.get(PinsOrm, order.pin_id)
    cert_code = f"LC{order.id:08d}{uuid.uuid4().hex[:6].upper()}"
    await db.execute(
        pg_insert(LicenseCertificatesOrm)
        .values(
            order_id=order.id,
            pin_id=order.pin_id,
            buyer_user_id=order.buyer_user_id,
            seller_user_id=order.seller_user_id,
            license_type="personal_use",
            content_sha256=pin.content_sha256 if pin else None,
            certificate_code=cert_code,
            paid_at=order.paid_at or now,
        )
        .on_conflict_do_nothing(constraint="uq_license_certificates_order_id")
    )

    await _notify_paid(db, order)
    return order


async def _notify_paid(db: AsyncSession, order: PinOrdersOrm) -> None:
    buyer = await db.get(UsersOrm, order.buyer_user_id)
    seller = await db.get(UsersOrm, order.seller_user_id)
    pin_link = f"{settings.FRONTEND_DOMAIN}/pin/{order.pin_id}"
    try:
        if buyer and buyer.email:
            send_email.delay(
                [buyer.email],
                "License purchase confirmed",
                {
                    "pin_id": order.pin_id,
                    "order_id": order.id,
                    "pin_link": pin_link,
                    "home_link": settings.FRONTEND_DOMAIN,
                },
                "mail_marketplace_order_paid_buyer.html",
            )
        if seller and seller.email:
            send_email.delay(
                [seller.email],
                "Your pin license was purchased",
                {
                    "pin_id": order.pin_id,
                    "order_id": order.id,
                    "pin_link": pin_link,
                    "seller_net_minor": order.seller_net_minor,
                    "currency": order.currency,
                    "home_link": settings.FRONTEND_DOMAIN,
                },
                "mail_marketplace_order_paid_seller.html",
            )
    except Exception:
        # Do not fail payment grant if broker/email is down
        pass


async def apply_sepay_webhook(db: AsyncSession, payload: dict) -> dict:
    transfer_type = payload.get("transferType")
    if transfer_type != "in":
        return {"success": True, "skipped": "not_in"}

    code = (payload.get("code") or "").strip().upper()
    # SePay may put full memo in code/content (e.g. "SEVQR DH…"); always normalize to DH….
    if code and not code.startswith("DH"):
        code = extract_payment_code_from_content(code) or code
    if not code.startswith("DH") and isinstance(payload.get("content"), str):
        code = extract_payment_code_from_content(payload["content"])
    if not code:
        return {"success": True, "skipped": "no_code"}

    amount = payload.get("transferAmount")
    try:
        amount_i = int(amount)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bad_amount")

    event_id = payload.get("id")
    if event_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing_event_id")

    order = await db.scalar(
        select(PinOrdersOrm).where(PinOrdersOrm.payment_code == str(code).upper())
    )
    if order is None:
        return {"success": True, "skipped": "unknown_code"}

    if order.charge_amount_vnd != amount_i:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="amount_mismatch")

    if order.status == "pending" and order.expires_at <= datetime.now(timezone.utc):
        await db.execute(
            update(PinOrdersOrm)
            .where(PinOrdersOrm.id == order.id)
            .values(status="cancelled", updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="order_expired")

    await mark_order_paid(
        db, order, provider_event_id=str(event_id), payload=payload
    )
    await db.commit()
    return {"success": True}


async def mock_mark_paid(db: AsyncSession, order_id: int, buyer_id: int) -> PinOrdersOrm:
    if not (settings.DEV_MODE and settings.MP_SEPAY_MOCK):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not_found")
    order = await db.get(PinOrdersOrm, order_id)
    if order is None or order.buyer_user_id != buyer_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    if order.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"order_{order.status}")
    payload = {
        "id": f"mock-{order.id}-{uuid.uuid4().hex[:8]}",
        "transferType": "in",
        "transferAmount": order.charge_amount_vnd,
        "code": order.payment_code,
        "content": order.payment_code,
    }
    order = await mark_order_paid(
        db, order, provider_event_id=str(payload["id"]), payload=payload
    )
    await db.commit()
    return order


async def cancel_expired_pending_sync_style(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(PinOrdersOrm)
        .where(
            PinOrdersOrm.status == "pending",
            PinOrdersOrm.expires_at <= now,
        )
        .values(status="cancelled", updated_at=now)
    )
    await db.commit()
    return result.rowcount or 0
