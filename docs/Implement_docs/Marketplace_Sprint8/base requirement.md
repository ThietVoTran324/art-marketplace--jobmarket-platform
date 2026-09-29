# Base requirement — Marketplace_Sprint8 (Phase 2.8 Seller payout)

**Input Plan #1.** Prerequisite: Marketplace Sprint0–7 **CLOSED** (orders + method verify + snapshot payout + media evidence).

## Gaps hiện tại

1. Buyer trả tiền vào STK platform; seller_net chỉ **snapshot** + admin mark tay — thiếu pipeline execute đầy đủ (state, attempt, adapter).
2. Payment method bank thiếu **mã ngân hàng** chuẩn; chủ TK optional → ops dễ chi nhầm.
3. Verify method = admin/seed — chưa eKYC; cần ToS rõ “seller chịu STK”.
4. SePay **không** chi hộ; Open Banking/API chi tiền chưa nối — cần khung gần đủ để cắm sau, **không** gọi live trong sprint.
5. Admin API pending/mark có; thiếu UI product + seller xem trạng thái payout.

## Mục tiêu sprint

1. Siết khai báo bank (mã NH + chủ TK) + giữ verify admin/seed + ToS.  
2. Pipeline payout: queue → validate → execute qua provider (`manual` / `stub`) → audit/attempt.  
3. Skeleton provider Open API **disabled** — chỉ thiếu credentials + HTTP thật.  
4. FE admin queue + seller status.  
5. Smoke không cần bank thật.

## Ngoài phạm vi

Gọi Open API / IB live · eKYC / micro-deposit · VNPay · refund · ví nội bộ · auto-schedule chi không admin.
