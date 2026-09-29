from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class CriterionOut(BaseModel):
    code: str
    current: int
    threshold: int
    passed: bool


class EligibilityOut(BaseModel):
    eligible: bool
    has_seller_role: bool
    criteria: list[CriterionOut]


class EnableSellingOut(BaseModel):
    roles: list[str]
    eligible: bool


class PaymentMethodIn(BaseModel):
    method_type: Literal["bank", "e_wallet"]
    display_name: str = Field(min_length=1, max_length=100)
    account_identifier: str = Field(min_length=1, max_length=200)
    bank_name: str | None = Field(default=None, max_length=120)
    bank_code: str | None = Field(default=None, max_length=20)
    account_holder: str | None = Field(default=None, max_length=120)
    is_primary: bool = False


class PaymentMethodPatchIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    account_identifier: str | None = Field(default=None, min_length=1, max_length=200)
    bank_name: str | None = Field(default=None, max_length=120)
    bank_code: str | None = Field(default=None, max_length=20)
    account_holder: str | None = Field(default=None, max_length=120)
    is_active: bool | None = None
    is_primary: bool | None = None


class PaymentMethodOut(BaseModel):
    id: int
    method_type: str
    display_name: str
    account_identifier: str
    bank_name: str | None = None
    bank_code: str | None = None
    account_holder: str | None = None
    is_active: bool
    is_primary: bool
    verification_status: str = "unverified"
    verified_at: datetime | None = None
    verified_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminPaymentMethodVerifyIn(BaseModel):
    verification_status: Literal["unverified", "verified"]


class PayoutConfigOut(BaseModel):
    commission_percent: float
    estimate_note: str
    price_minor: int | None = None
    commission_minor: int | None = None
    seller_net_minor: int | None = None


class ListingCreateIn(BaseModel):
    price_minor: int = Field(gt=0)
    currency: Literal["USD", "VND"] = "USD"
    attestation_accepted: bool = False


class ListingPatchIn(BaseModel):
    price_minor: int | None = Field(default=None, gt=0)
    currency: Literal["USD", "VND"] | None = None
    status: Literal["listed", "unlisted"] | None = None
    attestation_accepted: bool | None = None


class ListingOut(BaseModel):
    id: int
    pin_id: int
    seller_user_id: int
    license_type: str
    price_minor: int
    currency: str
    status: str
    attestation_accepted: bool = False
    attestation_version: str | None = None
    attested_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    buyer_user_id: int
    seller_user_id: int
    pin_id: int
    listing_id: int
    price_minor: int
    currency: str
    charge_amount_vnd: int
    payment_code: str
    provider: str
    status: str
    commission_percent: float | None = None
    commission_minor: int | None = None
    seller_net_minor: int | None = None
    payout_status: str
    expires_at: datetime
    paid_at: datetime | None = None
    created_at: datetime
    payment_url: str | None = None

    class Config:
        from_attributes = True


class PaymentInstructionsOut(BaseModel):
    payment_code: str
    charge_amount_vnd: int
    transfer_content: str
    bank_bin: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    account_name: str | None = None
    vietqr_image_url: str | None = None
    payment_url: str | None = None
    instructions: str


class PurchaseStateOut(BaseModel):
    state: str  # none | pending | owned
    order_id: int | None = None
    payment_code: str | None = None
    payment_url: str | None = None
    charge_amount_vnd: int | None = None
    sepay_mock_enabled: bool = False
    payment_instructions: PaymentInstructionsOut | None = None


class CheckoutPinOut(BaseModel):
    pin_id: int
    title: str | None = None
    rgb: str | None = None
    seller_user_id: int


class CheckoutPreviewOut(BaseModel):
    """Lazy checkout: draft = no DB bill yet; pending = order exists."""

    phase: str  # draft | pending | owned
    pin: CheckoutPinOut
    listing: ListingOut
    charge_amount_vnd: int
    order_id: int | None = None
    order: OrderOut | None = None
    payment_instructions: PaymentInstructionsOut | None = None
    sepay_mock_enabled: bool = False
    expires_at: datetime | None = None


class OrderCreateOut(BaseModel):
    order: OrderOut
    payment_url: str
    reused: bool = False
    payment_instructions: PaymentInstructionsOut | None = None


class AdminPayoutOut(BaseModel):
    order_id: int
    pin_id: int
    seller_user_id: int
    buyer_user_id: int
    paid_at: datetime | None = None
    currency: str
    price_minor: int
    seller_net_minor: int | None = None
    payout_amount_vnd: int | None = None
    payout_status: str
    payout_method_type: str | None = None
    payout_display_name: str | None = None
    payout_account_identifier: str | None = None
    payout_bank_name: str | None = None
    payout_bank_code: str | None = None
    payout_account_holder: str | None = None
    payout_marked_at: datetime | None = None
    payout_note: str | None = None


class AdminPayoutMarkIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class AdminPayoutExecuteIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    force_fail: bool = False


class SellerPayoutOut(BaseModel):
    order_id: int
    pin_id: int
    paid_at: datetime | None = None
    currency: str
    seller_net_minor: int | None = None
    payout_amount_vnd: int | None = None
    payout_status: str
    payout_marked_at: datetime | None = None
    payout_note: str | None = None


class CopyrightReportIn(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class CopyrightReportOut(BaseModel):
    id: int
    reporter_user_id: int
    pin_id: int
    reason: str
    status: str
    admin_note: str | None = None
    resolved_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CopyrightReportAdminPatchIn(BaseModel):
    status: Literal["resolved", "dismissed"]
    admin_note: str | None = Field(default=None, max_length=500)


class LicenseCertificateOut(BaseModel):
    id: int
    order_id: int
    pin_id: int
    buyer_user_id: int
    seller_user_id: int
    license_type: str
    content_sha256: str | None = None
    certificate_code: str
    paid_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

