"""Seller payout providers — manual / stub live; open_api skeleton only (no HTTP)."""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings


class PayoutProviderError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or code
        super().__init__(self.message)


class PayoutNotConfigured(PayoutProviderError):
    def __init__(self, message: str = "payout_provider_not_configured"):
        super().__init__("not_configured", message)


@dataclass(frozen=True)
class PayoutTransferRequest:
    order_id: int
    amount_vnd: int
    account_identifier: str
    account_holder: str | None
    bank_code: str | None
    bank_name: str | None
    method_type: str | None
    idempotency_key: str


@dataclass(frozen=True)
class PayoutTransferResult:
    success: bool
    provider_ref: str | None = None
    error: str | None = None


class BasePayoutProvider:
    name: str = "base"

    def transfer(self, req: PayoutTransferRequest, *, force_fail: bool = False) -> PayoutTransferResult:
        raise NotImplementedError


class ManualPayoutProvider(BasePayoutProvider):
    """Ops already transferred (or will mark); execute = bookkeeping success."""

    name = "manual"

    def transfer(self, req: PayoutTransferRequest, *, force_fail: bool = False) -> PayoutTransferResult:
        if force_fail:
            return PayoutTransferResult(success=False, error="manual_force_fail")
        return PayoutTransferResult(success=True, provider_ref=f"manual:{req.idempotency_key}")


class StubPayoutProvider(BasePayoutProvider):
    """Fake transfer for smoke / local — never moves money."""

    name = "stub"

    def transfer(self, req: PayoutTransferRequest, *, force_fail: bool = False) -> PayoutTransferResult:
        if force_fail:
            return PayoutTransferResult(success=False, error="stub_force_fail")
        return PayoutTransferResult(success=True, provider_ref=f"stub:{req.idempotency_key}")


class OpenApiPayoutProvider(BasePayoutProvider):
    """
    Skeleton for future Open Banking / disbursement API.

    Contract inputs are on PayoutTransferRequest. This sprint MUST NOT perform HTTP.
    """

    name = "open_api"

    def transfer(self, req: PayoutTransferRequest, *, force_fail: bool = False) -> PayoutTransferResult:
        _ = (req, force_fail)
        # Intentionally no HTTP. Enable only after credentials + real client exist.
        raise PayoutNotConfigured(
            "open_api_payout_disabled — wire bank Open API client then set MP_PAYOUT_PROVIDER"
        )


def get_payout_provider() -> BasePayoutProvider:
    name = (settings.MP_PAYOUT_PROVIDER or "manual").strip().lower()
    if name == "stub":
        return StubPayoutProvider()
    if name == "open_api":
        return OpenApiPayoutProvider()
    if name == "manual":
        return ManualPayoutProvider()
    raise PayoutNotConfigured(f"unknown_payout_provider:{name}")
