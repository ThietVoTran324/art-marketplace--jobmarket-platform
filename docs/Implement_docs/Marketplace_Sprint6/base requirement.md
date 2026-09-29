# Base requirement — Marketplace_Sprint6 (Phase 2.6)

**Input Plan #1.** Prerequisite: Marketplace Sprint0–5 CLOSED.

## Gaps hiện tại

1. Gate **P** đếm mọi `seller_payment_methods.is_active` — không có `verification_status` → method tự thêm = đủ P (demo/CV lỏng).
2. Settings tab **Seller payout** gộp CRUD; PinView còn form add-method tối thiểu + eligibility/enable — UX lẫn Selling vs Payment methods.
3. Buyer SePay: webhook HMAC gần đúng docs; FE luôn hiện **Mock pay**; live = env secret + base URL + ẩn mock + ops checklist (không invent create-payment SDK).

## Mục tiêu sprint

1. Xiết P: chỉ active **và** `verified`; seed + admin verify (seller không tự verify).  
2. Tách Settings **Payment methods** / **Selling**; PinView list-only.  
3. SePay live cutover: fail-closed ngoài mock; FE mock theo flag backend; doc ops.

## Ngoài phạm vi

Bank KYC API · pending/rejected enum · VNPay · refund · auto payout · Admin UI product.
