# Business Requirements — Marketplace_Sprint8 (Phase 2.8 Seller payout)

**Mức chi tiết:** ~3/10 (business). Schema/route → Plan #2.  
**SSOT hệ thống:** [`../../Planing_docs/marketplace/business_requirement.md`](../../Planing_docs/marketplace/business_requirement.md) (D2 payout STK/ví)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prerequisite:** Marketplace Sprint0–7 **CLOSED**

> **Plan #1 CHỐT** 2026-09-28 — `all suggest` từ debate payout.

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Seller khai method bank đủ để ops/chi sau này (mã NH + chủ TK) |
| 2 | Verify method giữ admin/seed; ToS self-responsibility STK |
| 3 | Sau order paid: hàng đợi payout đầy đủ (trạng thái + attempt + audit) |
| 4 | Execute chỉ admin/internal; amount chỉ từ snapshot order |
| 5 | Provider `manual` + `stub` chạy E2E; Open API skeleton **không** gọi live |
| 6 | Admin UI queue; seller xem trạng thái payout |

**Không** nối / gọi Open Banking API thật trong sprint này.

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Seller | CRUD method (field đủ); xem payout status; **không** kích hoạt chi tiền platform |
| Admin / ops | Verify method; duyệt/chi (manual mark hoặc stub execute) |
| Hệ thống | Queue từ order paid; idempotent; từ chối open_api khi chưa cấu hình |
| Open API (tương lai) | Adapter sẵn contract — tắt |

---

## 3. Quy tắc (CHỐT Plan #1)

| ID | CHỐT |
|----|------|
| S1 | Phase **2.8** · folder `Marketplace_Sprint8` |
| S2 | Verify ownership: admin/seed + ToS — **không** eKYC / micro-deposit |
| S3 | Bank: bắt buộc mã ngân hàng + tên chủ tài khoản |
| S4 | Provider: `manual` + `stub` bật; `open_api` skeleton **disabled** |
| S5 | Chỉ admin (hoặc job nội bộ privileged) được execute — seller read-only |
| S6 | Trạng thái: `pending` → `processing` → `paid` \| `failed`; `skipped`; legacy mark map về `paid` |
| S7 | Mỗi lần execute ghi attempt + audit |
| S8 | Idempotent: payout đã thành công không chi lại; retry chỉ từ `failed` |
| S9 | FE: admin queue + Settings seller (field mới + status gần đây) |
| S10 | Open API: NotConfigured / flag off — **cấm** HTTP bank trong sprint |
| S11 | Prove-done: smoke paid→queue→stub→idempotent |

Kế thừa: D2 không ví nội bộ · commission snapshot Sprint4 · method verified mới bán Sprint6.

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|-------|
| AC-01 | Tạo/sửa bank method thiếu mã NH hoặc chủ TK → bị từ chối rõ ràng |
| AC-02 | Order paid xuất hiện trong queue với đủ thông tin chi (số tiền net + đích) |
| AC-03 | Admin hoàn tất payout (manual hoặc stub) → trạng thái paid + attempt/audit |
| AC-04 | Execute lại order đã paid-out → conflict / no-op (không double pay) |
| AC-05 | Seller gọi execute (nếu lộ route) → 403 |
| AC-06 | Provider open_api / thiếu cấu hình → từ chối an toàn, không chuyển tiền |
| AC-07 | Seller và admin thấy trạng thái payout đọc được trên UI/API |
| AC-08 | Smoke PASS không cần bank/Open API thật |

---

## 5. Out of scope

Open API / IB live transfer · eKYC ownership · VNPay · refund/chargeback · ví nội bộ · auto payout schedule không admin · SePay disbursement (không có trên gói hiện tại).

---

## 6. Phụ thuộc / sync

- Sprint3–4 payment methods + order snapshot  
- Sprint6 `verification_status`  
- `security_followups` T2-S6-02: live disbursement API → **deferred**; adapter skeleton **in** Sprint8  
- T2-S6-05 Admin UI payout → **pulled into** Sprint8
