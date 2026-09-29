# Business Requirements — Marketplace_Sprint6 (Phase 2.6 Verify + SePay live)

**Mức chi tiết:** ~3/10 (business). Schema/route → Plan #2.  
**SSOT hệ thống:** [`../../Planing_docs/marketplace/business_requirement.md`](../../Planing_docs/marketplace/business_requirement.md)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prerequisite:** Marketplace Sprint0–5 **CLOSED**

> **Plan #1 CHỐT** — D1–D7 từ debate (xiết+seed + SePay live cùng phase).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | `verification_status` trên seller payment methods (`unverified` \| `verified`) |
| 2 | Gate P chỉ đếm active+verified; seed + admin set verified |
| 3 | Settings: Payment methods (CRUD) + Selling (eligibility/enable); PinView list-only |
| 4 | SePay buyer live cutover: webhook HMAC/ops; ẩn Mock pay khi mock off |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Seller | Thêm method → unverified; quản lý ở Settings; không tự verify |
| Admin | API verify/unverify method |
| Hệ thống / seed | Verify method demo; gate P; SePay webhook grant |
| Buyer | Checkout + chuyển khoản (live) hoặc mock (local) |

---

## 3. Quy tắc

| ID | CHỐT |
|----|------|
| D1 | Xiết + seed — không bypass eligibility |
| D2 | P = active **và** verified ≥ 1 |
| D3 | Enum MVP: `unverified` \| `verified` |
| D4 | Seller không tự verify |
| D5 | Settings Payment methods + Selling; PinView list/unlist + giá only |
| D6 | SePay live cùng phase; không auto-payout |
| D7 | Folder Marketplace_Sprint6 · Phase 2.6 |

Last-method guard (Sprint3): không thể làm P=0 (mất hết active+verified) khi còn pin `listed`.

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|-------|
| AC-01 | Method mới = unverified; user API không set status |
| AC-02 | P / enable / list chỉ với active+verified |
| AC-03 | Seed → demo sellers P pass |
| AC-04 | Admin verify/unverify |
| AC-05 | Settings tabs + PinView không CRUD method |
| AC-06 | Mock pay UI chỉ khi backend mock on |
| AC-07 | Prod: secret bắt buộc ngoài mock; HMAC + amount/code |
| AC-08 | Smoke Sprint6 PASS |
| AC-09 | sprint_map + README Phase 2.6 |

---

## 5. Ngoài phạm vi

Bank KYC · pending/rejected · VNPay · refund · DRM · Admin UI đầy đủ · đổi N/M/K
