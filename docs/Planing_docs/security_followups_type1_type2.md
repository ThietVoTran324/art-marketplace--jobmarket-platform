# Security follow-ups — Type 1 vs Type 2 (2026-08-08)

> Nguồn: cross-phase audit Phase 0 + Job Market + Marketplace.  
> **Type 1** = lỗ hổng/debt đã tồn tại trên code đã ship → **sửa ngay** (session này).  
> **Type 2** = chưa cần sửa riêng; làm kèm sprint / initiative tiếp theo → **note** vào doc sprint/backlog.

---

## Type 1 — FIXED (implement 2026-08-08)

| ID | Issue | Fix |
|----|-------|-----|
| T1-01 | `MP_SEPAY_MOCK` default + mock pay luôn mở | Default `False`; mock chỉ khi `DEV_MODE` **và** `MP_SEPAY_MOCK` |
| T1-02 | Webhook bỏ HMAC khi secret trống | Fail-closed trừ `DEV_MODE`+mock local |
| T1-03 | Access cookie nhận refresh JWT | `get_current_user_id` bắt `sub == "access"` |
| T1-04 | Original `/file` không re-check ACL | Re-check owner/license sau verify signature |
| T1-05 | `GET /companies/{id}` lộ reg/tax/VAT | Public → `CompanyPublicOut`; full chỉ owner |
| T1-06 | Xóa KYC doc sau terminal status | Chỉ cho request còn mở |
| T1-07 | JD/apps ownership không cần `employer` | Require `employer` + ownership trên mutate hiring |
| T1-08 | System BR §3.E attestation upload vs Sprint5 | Sửa system BR → listing-only (khớp S1) |

---

## Type 2 — DEFER (làm kèm phần tiếp theo)

| ID | Issue | Gắn vào | Ghi chú |
|----|-------|---------|---------|
| T2-01 | Copyright resolve không auto-unlist / revoke license | Unlist **DONE** Admin_Sprint3; revoke still later | Resolve → unlist |
| T2-02 | Rate-limit copyright reports | **DONE** Admin_Sprint3 | `MP_COPYRIGHT_REPORT_MAX` / window |
| T2-03 | Bắt buộc `PIN_MEDIA_SIGNING_SECRET` tách JWT | Media hardening (sau Sprint7) | Giảm blast radius |
| T2-04 | Strip `original_image` khỏi public `PinOut` | **DONE** Marketplace_Sprint7 | `has_original` + access audit |
| T2-05 | KYC/CV magic-byte + page-count | JobMarket upload harden | Sprint2 D17 residual |
| T2-06 | Dual `seller`+`employer` product rule | Planing marketplace+JM | Chưa cấm trong BR |
| T2-07 | VNPay / auto payout / chargeback | Marketplace post-Sprint4 | Manual/stub payout **DONE** Sprint8; live Open API = T2-S8-01 |
| T2-08 | Admin UI product (KYC/copyright/audit) | [`admin/`](admin/) Plan #1 DRAFT | API đã có; payout queue **DONE** Sprint8 |
| T2-S8-01 | Live Open Banking disbursement HTTP | Post credentials | Skeleton `open_api` NotConfigured |
| T2-S8-02 | eKYC / micro-deposit STK ownership | Post-volume | Sprint8 bank_code BIN only |
| T2-S8-03 | Auto cron payout (no admin click) | After live provider | Admin execute only |

Chi tiết Type 2 cũng mirror trong:

- [`deferred_and_out_of_scope_backlog.md`](deferred_and_out_of_scope_backlog.md) §G  
- [`../Implement_docs/Marketplace_Sprint5/README.md`](../Implement_docs/Marketplace_Sprint5/README.md)  
- [`../Implement_docs/Marketplace_Sprint8/SECURITY_FOLLOWUPS.md`](../Implement_docs/Marketplace_Sprint8/SECURITY_FOLLOWUPS.md)  
- [`job_market/README.md`](job_market/README.md) (pointer)
