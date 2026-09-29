# Plan mode decisions — Marketplace_Sprint6 (Phase 2.6)

> **Initiative:** Marketplace_Sprint6 — verify methods + SePay live  
> **Plan #2 CHỐT** — all suggest Q1–Q6 A

---

## Q&A (A = suggest)

| Q | A (CHỐT) | Why |
|---|----------|-----|
| Q1 Migration columns | `verification_status` CHECK + default `unverified`; `verified_at` timestamptz null; `verified_by` String(64) null (`seed` \| `admin:{id}`) | Đủ audit MVP không FK vòng |
| Q2 Alembic rev | `e7f8a9b0c1d2` revises `d6e7f8a9b0c1` | Linear head hiện tại |
| Q3 Admin API | `PATCH /admin/marketplace/payment-methods/{id}` body `{verification_status}` + audit | Reuse `require_roles("admin")` |
| Q4 Gate / drop guard | `count_verified_active`; drop chỉ block khi method đang counted và remaining verified=0 + còn listed | Khớp D2 |
| Q5 Mock FE flag | `sepay_mock_enabled` trên `PurchaseStateOut` (+ order create path nếu cần) = `DEV_MODE and MP_SEPAY_MOCK` | PinView ẩn nút |
| Q6 Seed | `scripts/seed_marketplace_verified_methods.py` — env `MP_SEED_VERIFY_USERNAMES` (comma) hoặc default demo list; tạo method nếu thiếu rồi verify | Idempotent |

---

## Decisions table

| ID | Decision |
|----|----------|
| D1 | Backfill existing rows → `unverified` |
| D2 | Index `(user_id)` giữ; filter verified in query (optional partial index later) |
| D3 | HMAC: raw `request.body()`; fail-closed ngoài mock |
| D4 | Smoke expects head `e7f8a9b0c1d2`; older MP smokes SQL-verify methods after create |
| D5 | Type2: bank KYC / pending-rejected / auto payout → SECURITY_FOLLOWUPS |

---

## Schema sketch

`seller_payment_methods`:
- `verification_status` NOT NULL DEFAULT `unverified`
- `verified_at` nullable
- `verified_by` nullable String(64)

## Routes sketch

- User: unchanged CRUD; Out includes status fields  
- Admin: PATCH verify  
- Purchase-state: `sepay_mock_enabled`  
- Webhook: unchanged path; audit raw body
