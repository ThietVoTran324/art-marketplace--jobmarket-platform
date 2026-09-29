from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import delete, func, insert, select, update

from app.api.rest.dependencies import db, user_id
from app.api.rest.marketplace.bank_codes import bank_name_for_code, validate_bank_code
from app.api.rest.marketplace.eligibility import (
    assert_can_create_listing,
    compute_eligibility,
)
from app.api.rest.marketplace.media_ready import assert_pin_media_ready
from app.api.rest.marketplace.orders import (
    apply_sepay_webhook,
    cancel_open_pendings_for_pin,
    compute_charge_amount_vnd,
    create_or_reuse_order,
    get_open_pending,
    mock_mark_paid,
    payment_instructions_for,
    payment_url_for,
    sepay_mock_enabled,
    verify_sepay_signature,
)
from app.celery.tasks import generate_pin_preview
from app.api.rest.marketplace.payment_methods import (
    assert_can_drop_active_method,
    clear_other_primaries,
    count_active_methods,
    count_verified_active_methods,
    get_owned_method,
    method_counts_toward_p,
)
from app.api.rest.marketplace.schemas import (
    CheckoutPinOut,
    CheckoutPreviewOut,
    CopyrightReportIn,
    CopyrightReportOut,
    EligibilityOut,
    EnableSellingOut,
    LicenseCertificateOut,
    ListingCreateIn,
    ListingOut,
    ListingPatchIn,
    OrderCreateOut,
    OrderOut,
    PaymentInstructionsOut,
    PaymentMethodIn,
    PaymentMethodOut,
    PaymentMethodPatchIn,
    PayoutConfigOut,
    PurchaseStateOut,
    SellerPayoutOut,
)
from app.api.rest.roles import assign_role
from app.api.rest.role_gates import assert_can_sell_on_marketplace
from app.config import settings
from app.postgresql.models import (
    CopyrightReportsOrm,
    LicenseCertificatesOrm,
    PinLicenseAccessOrm,
    PinListingsOrm,
    PinOrdersOrm,
    PinsOrm,
    SellerPaymentMethodsOrm,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/me/eligibility", response_model=EligibilityOut)
async def get_my_eligibility(user_id: user_id, db: db):
    result = await compute_eligibility(db, user_id)
    return result.as_dict()


@router.post("/me/enable-selling", response_model=EnableSellingOut)
async def enable_selling(user_id: user_id, db: db):
    await assert_can_sell_on_marketplace(db, user_id)
    result = await compute_eligibility(db, user_id)
    if not result.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "eligibility_not_met",
                "eligibility": result.as_dict(),
            },
        )
    roles = await assign_role(db, user_id, "seller")
    await db.commit()
    return EnableSellingOut(roles=sorted(roles), eligible=True)


@router.get("/me/payout-config", response_model=PayoutConfigOut)
async def get_payout_config(
    user_id: user_id,
    price_minor: int | None = Query(default=None, gt=0),
):
    pct = float(settings.MP_PLATFORM_COMMISSION_PERCENT)
    pct = max(0.0, min(100.0, pct))
    out = PayoutConfigOut(
        commission_percent=pct,
        estimate_note="Platform fee is deducted when your sale is paid out. There is no in-app wallet balance.",
    )
    if price_minor is not None:
        commission_minor = int(round(price_minor * pct / 100.0))
        out.price_minor = price_minor
        out.commission_minor = commission_minor
        out.seller_net_minor = price_minor - commission_minor
    return out


@router.get("/me/payouts", response_model=list[SellerPayoutOut])
async def list_my_payouts(
    user_id: user_id,
    db: db,
    limit: int = Query(default=30, ge=1, le=100),
):
    rows = await db.scalars(
        select(PinOrdersOrm)
        .where(
            PinOrdersOrm.seller_user_id == user_id,
            PinOrdersOrm.status == "paid",
        )
        .order_by(PinOrdersOrm.paid_at.desc().nulls_last(), PinOrdersOrm.id.desc())
        .limit(limit)
    )
    return [
        SellerPayoutOut(
            order_id=o.id,
            pin_id=o.pin_id,
            paid_at=o.paid_at,
            currency=o.currency,
            seller_net_minor=o.seller_net_minor,
            payout_amount_vnd=o.payout_amount_vnd,
            payout_status=o.payout_status,
            payout_marked_at=o.payout_marked_at,
            payout_note=o.payout_note,
        )
        for o in rows.all()
    ]


@router.get("/me/payment-methods", response_model=list[PaymentMethodOut])
async def list_payment_methods(user_id: user_id, db: db):
    rows = await db.scalars(
        select(SellerPaymentMethodsOrm)
        .where(SellerPaymentMethodsOrm.user_id == user_id)
        .order_by(
            SellerPaymentMethodsOrm.is_primary.desc(),
            SellerPaymentMethodsOrm.id.desc(),
        )
    )
    return list(rows.all())


@router.post(
    "/me/payment-methods",
    response_model=PaymentMethodOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment_method(body: PaymentMethodIn, user_id: user_id, db: db):
    active_before = await count_active_methods(db, user_id)
    make_primary = body.is_primary or active_before == 0
    if make_primary:
        await clear_other_primaries(db, user_id)

    bank_code = None
    bank_name = (body.bank_name or "").strip() or None
    account_holder = (body.account_holder or "").strip() or None
    if body.method_type == "bank":
        bank_code = validate_bank_code(body.bank_code)
        if not account_holder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="account_holder_required",
            )
        if not bank_name:
            bank_name = bank_name_for_code(bank_code)

    row = await db.scalar(
        insert(SellerPaymentMethodsOrm)
        .values(
            user_id=user_id,
            method_type=body.method_type,
            display_name=body.display_name.strip(),
            account_identifier=body.account_identifier.strip(),
            bank_name=bank_name,
            bank_code=bank_code,
            account_holder=account_holder,
            is_active=True,
            is_primary=make_primary,
            verification_status="unverified",
        )
        .returning(SellerPaymentMethodsOrm)
    )
    await db.commit()
    return row


@router.patch("/me/payment-methods/{method_id}", response_model=PaymentMethodOut)
async def patch_payment_method(
    method_id: int, body: PaymentMethodPatchIn, user_id: user_id, db: db
):
    row = await get_owned_method(db, user_id, method_id)
    values: dict = {}

    if body.display_name is not None:
        values["display_name"] = body.display_name.strip()
    if body.account_identifier is not None:
        values["account_identifier"] = body.account_identifier.strip()
    if body.bank_name is not None:
        values["bank_name"] = body.bank_name.strip() or None
    if body.bank_code is not None:
        values["bank_code"] = validate_bank_code(body.bank_code)
        if not values.get("bank_name") and body.bank_name is None:
            values["bank_name"] = bank_name_for_code(values["bank_code"])
    if body.account_holder is not None:
        values["account_holder"] = body.account_holder.strip() or None

    # Bank methods must keep holder + code after patch
    next_type = row.method_type
    next_holder = (
        values["account_holder"]
        if "account_holder" in values
        else row.account_holder
    )
    next_code = values["bank_code"] if "bank_code" in values else row.bank_code
    if next_type == "bank":
        if not next_holder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="account_holder_required",
            )
        if not next_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bank_code_required",
            )

    will_be_active = row.is_active if body.is_active is None else body.is_active
    if body.is_active is not None and body.is_active is False and row.is_active:
        dropping_p = method_counts_toward_p(row)
        remaining_verified = await count_verified_active_methods(db, user_id) - (
            1 if dropping_p else 0
        )
        await assert_can_drop_active_method(
            db,
            user_id,
            remaining_verified_after=remaining_verified,
            dropping_counts_toward_p=dropping_p,
        )
        values["is_active"] = False
        values["is_primary"] = False
    elif body.is_active is True:
        values["is_active"] = True

    if body.is_primary is True:
        if not will_be_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="inactive_cannot_be_primary",
            )
        await clear_other_primaries(db, user_id, keep_method_id=method_id)
        values["is_primary"] = True
    elif body.is_primary is False:
        values["is_primary"] = False

    if not values:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_changes")

    row = await db.scalar(
        update(SellerPaymentMethodsOrm)
        .where(SellerPaymentMethodsOrm.id == method_id)
        .values(**values)
        .returning(SellerPaymentMethodsOrm)
    )
    await db.commit()
    return row


@router.delete("/me/payment-methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(method_id: int, user_id: user_id, db: db):
    row = await get_owned_method(db, user_id, method_id)
    if row.is_active:
        dropping_p = method_counts_toward_p(row)
        remaining_verified = await count_verified_active_methods(db, user_id) - (
            1 if dropping_p else 0
        )
        await assert_can_drop_active_method(
            db,
            user_id,
            remaining_verified_after=remaining_verified,
            dropping_counts_toward_p=dropping_p,
        )
    await db.execute(
        delete(SellerPaymentMethodsOrm).where(SellerPaymentMethodsOrm.id == method_id)
    )
    await db.commit()
    return {"status": "ok"}


@router.get("/pins/{pin_id}/listing", response_model=ListingOut | None)
async def get_pin_listing(pin_id: int, user_id: user_id, db: db):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    listing = await db.scalar(
        select(PinListingsOrm).where(PinListingsOrm.pin_id == pin_id)
    )
    if listing is None:
        return None
    if listing.status != "listed" and listing.seller_user_id != user_id:
        return None
    return listing


@router.post(
    "/pins/{pin_id}/listing",
    response_model=ListingOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_relist_pin_listing(
    pin_id: int, body: ListingCreateIn, user_id: user_id, db: db
):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")
    if pin.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not pin owner")
    assert_pin_media_ready(pin)
    if not body.attestation_accepted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="attestation_required",
        )

    await assert_can_create_listing(db, user_id)

    existing = await db.scalar(
        select(PinListingsOrm).where(PinListingsOrm.pin_id == pin_id)
    )
    now = datetime.now(timezone.utc)
    attest_values = {
        "attestation_accepted": True,
        "attestation_version": settings.MP_ATTESTATION_VERSION,
        "attested_at": now,
    }
    if existing:
        price_changed = (
            existing.price_minor != body.price_minor
            or existing.currency != body.currency
        )
        listing = await db.scalar(
            update(PinListingsOrm)
            .where(PinListingsOrm.id == existing.id)
            .values(
                price_minor=body.price_minor,
                currency=body.currency,
                status="listed",
                license_type="personal_use",
                updated_at=now,
                **attest_values,
            )
            .returning(PinListingsOrm)
        )
        if price_changed:
            await cancel_open_pendings_for_pin(db, pin_id=pin_id)
    else:
        listing = await db.scalar(
            insert(PinListingsOrm)
            .values(
                pin_id=pin_id,
                seller_user_id=user_id,
                license_type="personal_use",
                price_minor=body.price_minor,
                currency=body.currency,
                status="listed",
                **attest_values,
            )
            .returning(PinListingsOrm)
        )
    await db.commit()
    # Soft watermark only while listed for sale
    generate_pin_preview.run(pin_id, watermarked=True)
    return listing


@router.patch("/listings/{listing_id}", response_model=ListingOut)
async def patch_listing(listing_id: int, body: ListingPatchIn, user_id: user_id, db: db):
    listing = await db.scalar(
        select(PinListingsOrm).where(PinListingsOrm.id == listing_id)
    )
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing_not_found")
    if listing.seller_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not listing owner")

    values: dict = {"updated_at": datetime.now(timezone.utc)}
    if body.price_minor is not None:
        values["price_minor"] = body.price_minor
    if body.currency is not None:
        values["currency"] = body.currency
    prev_status = listing.status
    if body.status is not None:
        if body.status == "listed":
            await assert_can_create_listing(db, user_id)
            if not body.attestation_accepted and not listing.attestation_accepted:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="attestation_required",
                )
            if body.attestation_accepted:
                values["attestation_accepted"] = True
                values["attestation_version"] = settings.MP_ATTESTATION_VERSION
                values["attested_at"] = datetime.now(timezone.utc)
        values["status"] = body.status
    elif body.attestation_accepted is True:
        values["attestation_accepted"] = True
        values["attestation_version"] = settings.MP_ATTESTATION_VERSION
        values["attested_at"] = datetime.now(timezone.utc)

    if len(values) == 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no_changes")

    price_changed = (
        (body.price_minor is not None and body.price_minor != listing.price_minor)
        or (body.currency is not None and body.currency != listing.currency)
    )

    listing = await db.scalar(
        update(PinListingsOrm)
        .where(PinListingsOrm.id == listing_id)
        .values(**values)
        .returning(PinListingsOrm)
    )
    if price_changed:
        await cancel_open_pendings_for_pin(db, pin_id=listing.pin_id)
    await db.commit()

    if body.status is not None and body.status != prev_status:
        generate_pin_preview.run(
            listing.pin_id, watermarked=(listing.status == "listed")
        )
    return listing


def _order_out(order: PinOrdersOrm) -> OrderOut:
    data = OrderOut.model_validate(order)
    data.payment_url = payment_url_for(order)
    return data


@router.get("/pins/{pin_id}/purchase-state", response_model=PurchaseStateOut)
async def purchase_state(pin_id: int, user_id: user_id, db: db):
    mock_on = sepay_mock_enabled()
    owned = await db.scalar(
        select(PinLicenseAccessOrm.id).where(
            PinLicenseAccessOrm.user_id == user_id,
            PinLicenseAccessOrm.pin_id == pin_id,
        )
    )
    if owned is not None:
        return PurchaseStateOut(state="owned", sepay_mock_enabled=mock_on)

    pending = await get_open_pending(db, buyer_id=user_id, pin_id=pin_id)
    if pending is not None:
        # Pin detail only needs a continue link — full pay UI lives on /checkout.
        return PurchaseStateOut(
            state="pending",
            order_id=pending.id,
            payment_code=pending.payment_code,
            charge_amount_vnd=pending.charge_amount_vnd,
            sepay_mock_enabled=mock_on,
            payment_instructions=None,
            payment_url=None,
        )
    return PurchaseStateOut(state="none", sepay_mock_enabled=mock_on)


def _checkout_pin(pin: PinsOrm) -> CheckoutPinOut:
    return CheckoutPinOut(
        pin_id=pin.id,
        title=pin.title,
        rgb=pin.rgb,
        seller_user_id=pin.user_id,
    )


async def _build_checkout_preview(
    db, *, user_id: int, pin: PinsOrm, listing: PinListingsOrm
) -> CheckoutPreviewOut:
    mock_on = sepay_mock_enabled()
    listing_out = ListingOut.model_validate(listing)
    charge = compute_charge_amount_vnd(listing.price_minor, listing.currency)

    owned = await db.scalar(
        select(PinLicenseAccessOrm.id).where(
            PinLicenseAccessOrm.user_id == user_id,
            PinLicenseAccessOrm.pin_id == pin.id,
        )
    )
    if owned is not None:
        return CheckoutPreviewOut(
            phase="owned",
            pin=_checkout_pin(pin),
            listing=listing_out,
            charge_amount_vnd=charge,
            sepay_mock_enabled=mock_on,
        )

    pending = await get_open_pending(db, buyer_id=user_id, pin_id=pin.id)
    if pending is not None:
        stale = (
            pending.listing_id != listing.id
            or pending.price_minor != listing.price_minor
            or pending.currency != listing.currency
        )
        if stale:
            await db.execute(
                update(PinOrdersOrm)
                .where(PinOrdersOrm.id == pending.id, PinOrdersOrm.status == "pending")
                .values(status="cancelled", updated_at=datetime.now(timezone.utc))
            )
            await db.commit()
            pending = None
        else:
            instr = PaymentInstructionsOut(**payment_instructions_for(pending))
            return CheckoutPreviewOut(
                phase="pending",
                pin=_checkout_pin(pin),
                listing=listing_out,
                charge_amount_vnd=pending.charge_amount_vnd,
                order_id=pending.id,
                order=_order_out(pending),
                payment_instructions=instr,
                sepay_mock_enabled=mock_on,
                expires_at=pending.expires_at,
            )

    return CheckoutPreviewOut(
        phase="draft",
        pin=_checkout_pin(pin),
        listing=listing_out,
        charge_amount_vnd=charge,
        sepay_mock_enabled=mock_on,
    )


@router.get("/pins/{pin_id}/checkout", response_model=CheckoutPreviewOut)
async def checkout_preview_by_pin(pin_id: int, user_id: user_id, db: db):
    """Lazy checkout: no bill until POST /pins/{id}/orders from the checkout page."""
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")
    if pin.user_id == user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="cannot_buy_own_pin")
    listing = await db.scalar(
        select(PinListingsOrm).where(
            PinListingsOrm.pin_id == pin_id, PinListingsOrm.status == "listed"
        )
    )
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing_not_found")
    return await _build_checkout_preview(db, user_id=user_id, pin=pin, listing=listing)


@router.get("/me/orders/{order_id}/checkout", response_model=CheckoutPreviewOut)
async def checkout_preview_by_order(order_id: int, user_id: user_id, db: db):
    order = await db.get(PinOrdersOrm, order_id)
    if order is None or order.buyer_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    pin = await db.get(PinsOrm, order.pin_id)
    listing = await db.get(PinListingsOrm, order.listing_id)
    if pin is None or listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="listing_not_found")
    if order.status == "paid":
        return CheckoutPreviewOut(
            phase="owned",
            pin=_checkout_pin(pin),
            listing=ListingOut.model_validate(listing),
            charge_amount_vnd=order.charge_amount_vnd,
            order_id=order.id,
            order=_order_out(order),
            sepay_mock_enabled=sepay_mock_enabled(),
        )
    if order.status != "pending" or order.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"order_{order.status}")
    instr = PaymentInstructionsOut(**payment_instructions_for(order))
    return CheckoutPreviewOut(
        phase="pending",
        pin=_checkout_pin(pin),
        listing=ListingOut.model_validate(listing),
        charge_amount_vnd=order.charge_amount_vnd,
        order_id=order.id,
        order=_order_out(order),
        payment_instructions=instr,
        sepay_mock_enabled=sepay_mock_enabled(),
        expires_at=order.expires_at,
    )


@router.post(
    "/pins/{pin_id}/orders",
    response_model=OrderCreateOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_pin_order(pin_id: int, user_id: user_id, db: db):
    before = await get_open_pending(db, buyer_id=user_id, pin_id=pin_id)
    order = await create_or_reuse_order(db, buyer_id=user_id, pin_id=pin_id)
    reused = before is not None and before.id == order.id
    instr = PaymentInstructionsOut(**payment_instructions_for(order))
    url = instr.payment_url or payment_url_for(order)
    return OrderCreateOut(
        order=_order_out(order),
        payment_url=url,
        reused=reused,
        payment_instructions=instr,
    )


@router.get("/me/orders/{order_id}", response_model=OrderOut)
async def get_my_order(order_id: int, user_id: user_id, db: db):
    order = await db.get(PinOrdersOrm, order_id)
    if order is None or order.buyer_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    return _order_out(order)


@router.post("/me/orders/{order_id}/cancel", response_model=OrderOut)
async def cancel_my_order(order_id: int, user_id: user_id, db: db):
    order = await db.get(PinOrdersOrm, order_id)
    if order is None or order.buyer_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="order_not_found")
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"order_{order.status}"
        )
    order = await db.scalar(
        update(PinOrdersOrm)
        .where(PinOrdersOrm.id == order_id)
        .values(status="cancelled", updated_at=datetime.now(timezone.utc))
        .returning(PinOrdersOrm)
    )
    await db.commit()
    return _order_out(order)


@router.post("/webhooks/sepay")
async def sepay_webhook(request: Request, db: db):
    import json

    raw = await request.body()
    verify_sepay_signature(
        raw,
        request.headers.get("X-SePay-Signature")
        or request.headers.get("x-sepay-signature"),
        request.headers.get("X-SePay-Timestamp")
        or request.headers.get("x-sepay-timestamp"),
    )
    try:
        payload = json.loads(raw.decode("utf-8") or "{}")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json"
        ) from e
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json")
    return await apply_sepay_webhook(db, payload)


@router.post("/dev/mock-sepay-paid/{order_id}", response_model=OrderOut)
async def mock_sepay_paid(order_id: int, user_id: user_id, db: db):
    order = await mock_mark_paid(db, order_id, user_id)
    return _order_out(order)


@router.post(
    "/pins/{pin_id}/copyright-reports",
    response_model=CopyrightReportOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_copyright_report(
    pin_id: int, body: CopyrightReportIn, user_id: user_id, db: db
):
    pin = await db.scalar(select(PinsOrm).where(PinsOrm.id == pin_id))
    if pin is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="pin not found")

    window = max(1, int(settings.MP_COPYRIGHT_REPORT_WINDOW_SECONDS))
    max_reports = max(1, int(settings.MP_COPYRIGHT_REPORT_MAX))
    since = datetime.now(timezone.utc) - timedelta(seconds=window)
    recent = await db.scalar(
        select(func.count())
        .select_from(CopyrightReportsOrm)
        .where(
            CopyrightReportsOrm.reporter_user_id == user_id,
            CopyrightReportsOrm.created_at >= since,
        )
    )
    if int(recent or 0) >= max_reports:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="copyright_report_rate_limited",
        )

    row = await db.scalar(
        insert(CopyrightReportsOrm)
        .values(
            reporter_user_id=user_id,
            pin_id=pin_id,
            reason=body.reason.strip(),
            status="open",
        )
        .returning(CopyrightReportsOrm)
    )
    await db.commit()
    return row


@router.get("/me/certificates/by-pin/{pin_id}", response_model=LicenseCertificateOut | None)
async def get_my_certificate_for_pin(pin_id: int, user_id: user_id, db: db):
    row = await db.scalar(
        select(LicenseCertificatesOrm)
        .where(
            LicenseCertificatesOrm.pin_id == pin_id,
            LicenseCertificatesOrm.buyer_user_id == user_id,
        )
        .order_by(LicenseCertificatesOrm.id.desc())
    )
    return row


@router.get("/me/certificates/{order_id}", response_model=LicenseCertificateOut)
async def get_my_certificate(order_id: int, user_id: user_id, db: db):
    row = await db.scalar(
        select(LicenseCertificatesOrm).where(LicenseCertificatesOrm.order_id == order_id)
    )
    if row is None or row.buyer_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="certificate_not_found"
        )
    return row
