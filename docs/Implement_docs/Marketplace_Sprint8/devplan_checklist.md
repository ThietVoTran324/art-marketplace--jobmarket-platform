# Devplan checklist — Marketplace_Sprint8

**Prerequisite:** Plan #2 CHỐT · head `a9b0c1d2e3f4`  
**CLOSED:** 2026-09-28 · Alembic `b0c1d2e3f4a5` · `scripts/smoke_marketplace_sprint8.py` → `ALL_SMOKE_PASS`

## P1 — Schema

- [x] Migration `b0c1d2e3f4a5`: bank_code, payout_bank_code, status widen + manual→paid, payout_attempts
- [x] Models + snapshot bank_code on paid

## P2 — Methods

- [x] Require bank_code + account_holder for bank; static BIN validate
- [x] FE Settings fields + ToS line

## P3 — Providers + execute

- [x] `manual` / `stub` / `open_api` (NotConfigured)
- [x] Admin execute + mark-paid; attempt log; idempotent
- [x] `GET /marketplace/me/payouts`

## P4 — FE Admin

- [x] `/admin/marketplace/payouts` list + execute/mark

## P5 — Close

- [x] Smoke Sprint8 ALL_SMOKE_PASS
- [x] SECURITY_FOLLOWUPS + map CLOSED
