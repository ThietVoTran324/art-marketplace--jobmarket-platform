"""Known Viet Nam bank BINs (Napas) for seller payout destination validation."""
from __future__ import annotations

# Subset sufficient for MVP; extend as ops needs.
VN_BANK_BINS: dict[str, str] = {
    "970415": "VietinBank",
    "970436": "Vietcombank",
    "970418": "BIDV",
    "970405": "Agribank",
    "970422": "MB Bank",
    "970407": "Techcombank",
    "970432": "VPBank",
    "970423": "TPBank",
    "970403": "Sacombank",
    "970437": "HDBank",
    "970441": "VIB",
    "970448": "OCB",
    "970454": "VietABank",
    "970429": "SCB",
    "970414": "Maritime Bank (MSB)",
    "970416": "ACB",
    "970426": "MSB",
    "970431": "Eximbank",
    "970443": "SHB",
    "970449": "LienVietPostBank",
}


def normalize_bank_code(raw: str | None) -> str | None:
    if raw is None:
        return None
    code = "".join(ch for ch in raw.strip() if ch.isalnum())
    return code or None


def validate_bank_code(raw: str | None) -> str:
    code = normalize_bank_code(raw)
    if not code or code not in VN_BANK_BINS:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid_bank_code",
        )
    return code


def bank_name_for_code(code: str) -> str | None:
    return VN_BANK_BINS.get(code)
