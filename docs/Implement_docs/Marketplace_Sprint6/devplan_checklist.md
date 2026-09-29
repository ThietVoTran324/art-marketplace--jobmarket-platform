# Dev plan checklist — Marketplace_Sprint6 (Phase 2.6)

## P0 — Docs / map

- [x] PLANNING_TRIO + BR + base + plan_mode_decisions
- [x] sprint_map + README Phase 2.6 row (OPEN → CLOSED)

## P1 — Schema + eligibility

- [x] Migration `e7f8a9b0c1d2`
- [x] Model + schemas Out
- [x] Gate P + last-method guard verified
- [x] Create method always unverified

## P2 — Admin + seed

- [x] Admin PATCH verify + audit
- [x] `scripts/seed_marketplace_verified_methods.py`

## P3 — SePay live FE/BE

- [x] `sepay_mock_enabled` on purchase-state
- [x] PinView hide Mock pay when false
- [x] `.env.example` comments live vs mock
- [x] Ops notes in SECURITY_FOLLOWUPS

## P4 — FE Settings / PinView

- [x] Tabs: payment + selling (+ payout alias)
- [x] Payment methods badges
- [x] Selling: eligibility + enable
- [x] PinView: remove add-method; CTA Settings

## P5 — Smoke + close

- [x] `scripts/smoke_marketplace_sprint6.py`
- [x] Fix older MP smokes (verify method after create)
- [x] ALL_SMOKE_PASS · map CLOSED
