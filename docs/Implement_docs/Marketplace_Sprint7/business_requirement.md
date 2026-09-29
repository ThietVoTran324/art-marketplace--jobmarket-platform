# Business Requirements — Marketplace_Sprint7 (Phase 2.7 Media evidence)

**Mức chi tiết:** ~3/10 (business). Schema/route → Plan #2.  
**SSOT hệ thống:** [`../../Planing_docs/marketplace/business_requirement.md`](../../Planing_docs/marketplace/business_requirement.md) (D3 watermark static)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prerequisite:** Marketplace Sprint0–6 **CLOSED**

> **Plan #1 CHỐT** — all suggest từ debate (evidence-first, payout sau).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Preview công khai mang **bằng chứng nhìn thấy** (logo + text NOT LICENSED / PREVIEW) |
| 2 | Không cho **list** pin thiếu original / preview watermark / `content_sha256` |
| 3 | API public **không** lộ path `original_image` |
| 4 | Mỗi lần truy cập original (authorized) có **audit** truy vết |
| 5 | Smoke: unpaid chỉ preview có dấu; owner/buyer original + audit |

**Không** ship payout seller, DRM, invisible watermark.

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Visitor / unpaid | Xem/copy preview có dấu; không original |
| Owner | Preview + original; chịu ảnh hưởng strip path trên API public |
| Buyer paid | Original + certificate/hash (Sprint5) |
| Seller | Phải đủ media pipeline mới list; tranh chấp dựa watermark + hash/cert/log |
| Hệ thống | Tạo/reprocess preview; ghi audit original |

---

## 3. Quy tắc (CHỐT Plan #1)

| ID | CHỐT |
|----|------|
| S1 | Phase **2.7** · folder `Marketplace_Sprint7` |
| S2 | Watermark = logo **+** text cố định (`PREVIEW · NOT LICENSED` + brand) |
| S3 | Listed thiếu media/hash → **block list** + thông báo (không bắt buộc auto-reprocess trong AC tối thiểu) |
| S4 | Strip `original_image` mọi `PinOut` public (kéo T2-04) |
| S5 | Audit tối thiểu: mint signed URL **và** hit `/file` |
| S6 | Invisible / per-viewer mark → **Out** |
| S7 | Tắt chuột phải → **Out** (không AC chính) |

Kế thừa: D3 static watermark · không DRM · ACL original owner ∪ `pin_license_access`.

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|-------|
| AC-01 | Preview public có watermark nhìn được (logo + text theo S2) |
| AC-02 | Pin thiếu original/preview/hash không list được; seller nhận lý do rõ |
| AC-03 | Response pin public không chứa `original_image` (hoặc luôn null) |
| AC-04 | Non-owner unpaid không lấy original (403 / fail signed) |
| AC-05 | Mint URL original và GET `/file` thành công đều ghi audit (uid, pin, time, IP tối thiểu) |
| AC-06 | Smoke PASS: unpaid preview có dấu; owner/buyer original; audit có dòng |

---

## 5. Out of scope

Payout / chuyển tiền seller · DRM · steganography · per-viewer fingerprint · chặn screenshot · SePay/order changes · Admin forensics UI đầy đủ · bắt buộc `PIN_MEDIA_SIGNING_SECRET` tách JWT (T2-03 — vẫn Type2 trừ khi Plan #2 kéo nhẹ).

---

## 6. Phụ thuộc / sync

- Sprint1 media dirs + Celery preview  
- Sprint5 `content_sha256` + certificates  
- `security_followups`: T2-04 → **pulled into Sprint7**
