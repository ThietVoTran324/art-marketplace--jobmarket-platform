# Plan #2 decisions — Marketplace_Sprint8 (Phase 2.8)

> **CHỐT** 2026-09-28 — `all suggest` từ Plan #2 quiz.  
> Prerequisite Alembic head: `a9b0c1d2e3f4` → ship `b0c1d2e3f4a5`

| ID | CHỐT |
|----|------|
| T1 | Migration `b0c1d2e3f4a5`: `bank_code` methods + `payout_bank_code` order; widen payout_status; `payout_attempts` |
| T2 | `bank_code` = mã BIN/Napas (string) + validate list tĩnh |
| T3 | Legacy `manual` → `paid`; CHECK `pending\|processing\|paid\|failed\|skipped` |
| T4 | `payout_providers`: `manual`, `stub`, `open_api` (NotConfigured); `MP_PAYOUT_PROVIDER` default `manual` |
| T5 | `POST .../payouts/{id}/execute` + giữ `mark-paid` = manual success shortcut |
| T6 | Stub success; `force_fail` admin-only → `failed` |
| T7 | Open API class + contract — **zero HTTP** |
| T8 | `GET /marketplace/me/payouts` |
| T9 | FE `/admin/marketplace/payouts` |
| T10 | Settings: bank_code + account_holder required; block payouts gần đây |
| T11 | Snapshot `bank_code` lúc order paid |
| T12 | `scripts/smoke_marketplace_sprint8.py` |

## Sketch

- Attempts: id, order_id, provider, status (`started|success|failed`), error, actor_user_id, created_at  
- Amount chỉ từ `payout_amount_vnd` / seller_net snapshot  
- Seller không execute
