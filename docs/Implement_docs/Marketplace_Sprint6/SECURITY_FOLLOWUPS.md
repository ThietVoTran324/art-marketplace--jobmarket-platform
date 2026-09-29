# Security Type 2 — Marketplace_Sprint6 (defer)

## Type 2 (defer)

| ID | Việc | Khi nào |
|----|------|---------|
| T2-S6-01 | Bank / e-wallet KYC hoặc e-KYC API; enum `pending`/`rejected` | Post-demo verify product |
| T2-S6-02 | Auto bank payout to seller primary method (SePay **không** có API chi tiền trên gói webhook) | **→ Sprint8 adapter sẵn; live Open API Type2** |
| T2-S6-05 | Admin UI product cho pending payouts (API `GET/POST /admin/marketplace/payouts/*` đã có) | Admin Ops stream |
| T2-S6-03 | Admin UI product cho verify queue | **DONE** — `/admin/marketplace/payment-methods` + GET list |
| T2-S6-04 | VNPay · chargeback automation | Post-SePay expand |

## SePay live ops (ship checklist — not code debt)

1. Merchant SePay + bank account linked  
2. Webhook URL `https://{API}/marketplace/webhooks/sepay` · Auth HMAC-SHA256  
3. Payment code prefix matches `DH…` (SePay default; app `make_payment_code`)  
3b. **VietinBank API Banking:** buyer memo / VietQR `addInfo` must be `SEVQR DH…` (`MP_SEPAY_TRANSFER_CONTENT_PREFIX`) — otherwise SePay never syncs the transfer (banner on bank account page) 
4. Env: `MP_SEPAY_WEBHOOK_SECRET`, `MP_SEPAY_PAYMENT_BASE_URL`, `MP_SEPAY_MOCK=false`, `DEV_MODE=false`  
5. Confirm delivery logs Success on test transfer  

Xem [`../../Planing_docs/security_followups_type1_type2.md`](../../Planing_docs/security_followups_type1_type2.md).
