# Marketplace — sprint map (synced)

> **Sync:** 2026-09-28 — Sprint8 **CLOSED** (Seller payout, `b0c1d2e3f4a5`). Sprint0–8 COMPLETE.  
> **SSOT nghiệp vụ:** [`business_requirement.md`](business_requirement.md)  
> **Blocks:** [`phase0_market_and_block_classification.md`](phase0_market_and_block_classification.md)  
> **Deferred:** [`../deferred_and_out_of_scope_backlog.md`](../deferred_and_out_of_scope_backlog.md) MP-* / refund  
> **Trạng thái map:** **Synced** — Sprint0–8 **COMPLETE**.

---

## 1. Bảng map

| Phase | Sprint folder | Mục tiêu shippable | Phụ thuộc | Case |
|-------|---------------|--------------------|-----------|------|
| **0-market** | `Marketplace_Sprint0` | `created_at`; `pin_stats`; unique likes/follows; **wipe pin cũ OK** nếu cần | JM CLOSED | C08, C10 |
| **2.1** | `Marketplace_Sprint1` | Preview/original; static watermark; ACL + signed URL | Sprint0 | C01–C04 |
| **2.2** | `Marketplace_Sprint2` | Gate N=5/M=100/K=10 + payment method; role `seller`; listing 1-shot personal license | Sprint0+1 | C06–C07, C11 |
| **2.3** | `Marketplace_Sprint3` | Seller payment_methods (bank/e-wallet); không ví nội bộ | Sprint2 | C07 |
| **2.4** | `Marketplace_Sprint4` | Orders; SePay; USD default (+VND); grant access; **no refund** | Sprint1–3 | C04–C05, C12–C13 |
| **2.5** | `Marketplace_Sprint5` | Copyright report + hash + certificate | Sprint2+4 | C09 |
| **2.6** | `Marketplace_Sprint6` | Method `verification_status` + seed/admin; Settings Payment/Selling; SePay live cutover | Sprint3–5 | P gate · SePay |
| **2.7** | `Marketplace_Sprint7` | Preview evidence watermark; list media gate; strip `original_image`; original access audit | Sprint1+5+6 | Evidence |
| **2.8** | `Marketplace_Sprint8` | Seller payout pipeline (manual/stub); bank_code; Open API skeleton off | Sprint4+6+7 | Payout |

```mermaid
flowchart LR
  S0["Sprint0\n0-market"] --> S1["Sprint1\n2.1 Media"]
  S1 --> S2["Sprint2\n2.2 Listing+gate"]
  S2 --> S3["Sprint3\n2.3 Payout method"]
  S1 --> S4["Sprint4\n2.4 SePay order"]
  S2 --> S4
  S3 --> S4
  S4 --> S5["Sprint5\n2.5 Copyright"]
  S2 --> S5
  S3 --> S6["Sprint6\n2.6 Verify+SePay"]
  S4 --> S6
  S5 --> S6
  S1 --> S7["Sprint7\n2.7 Media evidence"]
  S5 --> S7
  S6 --> S7
  S4 --> S8["Sprint8\n2.8 Seller payout"]
  S6 --> S8
  S7 --> S8
```

**Hard rules**

1. Không Sprint4 trước Sprint0+1 CLOSED.  
2. Không implement refund/return.  
3. Pin cũ: được truncate/wipe khi conflict (D10).  
4. Sprint7: evidence-first — **không** DRM / payout.

---

## 2. Chi tiết sprint

### Marketplace_Sprint0 — 0-market data

**In:** migrations data foundation; unique constraints; optional wipe pins + related rows nếu pipeline mới conflict; smoke C08/C10.  
**Out:** UI bán; watermark đầy đủ (có thể stub path).

### Marketplace_Sprint1 — Media 2.1

**In:** original/preview dirs; Celery static watermark; public serve preview; original ACL + signed URL.  
**Out:** Checkout.

### Marketplace_Sprint2 — Listing + gate

**In:** eligibility engine (N/M/K + method); assign `seller`; license one-shot personal; FE bán trên CreatePin/PinView.  
**Out:** Charge thật (sandbox mock OK).

### Marketplace_Sprint3 — Payment methods

**In:** CRUD payout method; gate phụ thuộc method; commission % config.  
**Out:** Buyer charge.

### Marketplace_Sprint4 — Order + SePay

**In:** order states; SePay webhook idempotent; USD default; VND supported; email sau paid; block self-buy + email gate.  
**Out:** VNPay; refund.

### Marketplace_Sprint5 — Copyright

**In:** attestation; hash; report + admin API; certificate tối thiểu.  
**Out:** Admin UI product.

### Marketplace_Sprint6 — Verify methods + SePay live

**In:** `verification_status` + gate P verified; seed/admin verify; Settings Payment methods + Selling; PinView list-only; SePay mock UI gate + live ops.  
**Out:** Bank KYC API; VNPay; auto payout; Admin UI verify queue.

### Marketplace_Sprint7 — Media evidence 2.7

**In:** watermark logo+text trên preview; block list nếu thiếu original/preview/hash; strip `original_image` public PinOut (T2-04); audit mint + hit signed original.  
**Out:** DRM; invisible mark; per-viewer fingerprint; payout seller; tắt chuột phải như AC chính.

### Marketplace_Sprint8 — Seller payout 2.8

**In:** bank_code + account_holder bắt buộc; payout pipeline (pending→processing→paid/failed); attempt + audit; provider manual/stub; Open API skeleton **off**; Admin UI queue; seller status.  
**Out:** Open API/IB live; eKYC; VNPay; refund; auto-schedule không admin.

---

## 3. Implement_docs

| Sprint | Path | Status |
|--------|------|--------|
| 0 | [`../../Implement_docs/Marketplace_Sprint0/`](../../Implement_docs/Marketplace_Sprint0/) | **CLOSED** · `c9d0e1f2a3b4` |
| 1 | [`../../Implement_docs/Marketplace_Sprint1/`](../../Implement_docs/Marketplace_Sprint1/) | **CLOSED** · `d0e1f2a3b4c5` |
| 2 | [`../../Implement_docs/Marketplace_Sprint2/`](../../Implement_docs/Marketplace_Sprint2/) | **CLOSED** · `e1f2a3b4c5d6` |
| 3 | [`../../Implement_docs/Marketplace_Sprint3/`](../../Implement_docs/Marketplace_Sprint3/) | **CLOSED** · `f2a3b4c5d6e7` |
| 4 | [`../../Implement_docs/Marketplace_Sprint4/`](../../Implement_docs/Marketplace_Sprint4/) | **CLOSED** · `a3b4c5d6e7f8` |
| 5 | [`../../Implement_docs/Marketplace_Sprint5/`](../../Implement_docs/Marketplace_Sprint5/) | **CLOSED** · `b4c5d6e7f8a9` |
| 6 | [`../../Implement_docs/Marketplace_Sprint6/`](../../Implement_docs/Marketplace_Sprint6/) | **CLOSED** · `e7f8a9b0c1d2` |
| 7 | [`../../Implement_docs/Marketplace_Sprint7/`](../../Implement_docs/Marketplace_Sprint7/) | **CLOSED** · `a9b0c1d2e3f4` |
| 8 | [`../../Implement_docs/Marketplace_Sprint8/`](../../Implement_docs/Marketplace_Sprint8/) | **CLOSED** · `b0c1d2e3f4a5` |

Quy trình mỗi sprint: base → Plan #1 BR → Plan #2 tech + checklist → code → đóng → cập nhật README.

---

## 4. Trạng thái

| Hạng mục | Status |
|----------|--------|
| Plan #1 BR hệ thống | **CHỐT** 2026-08-08 |
| Sprint map | **Synced** 2026-09-28 |
| Implement Sprint0–7 | **CLOSED** |
| Sprint8 | **CLOSED** 2026-09-28 · `b0c1d2e3f4a5` · smoke PASS |
| Next | Open API live disbursement (Type2) khi có credentials |
