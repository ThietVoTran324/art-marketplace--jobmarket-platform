# Base requirement — Marketplace_Sprint7 (Phase 2.7 Media evidence)

**Input Plan #1.** Prerequisite: Marketplace Sprint0–6 **CLOSED** (media Sprint1 + cert/hash Sprint5 + SePay live Sprint6).

## Gaps hiện tại

1. Preview watermark **static logo** — dễ crop; thiếu chữ đọc được kiểu “NOT LICENSED / PREVIEW” cho tranh chấp.
2. Pin `listed` có thể thiếu / lệch pipeline (legacy `image` không watermark, thiếu `content_sha256`) mà vẫn bán.
3. Public `PinOut` còn field **`original_image`** (path disk) — T2-04.
4. Signed original download **không** có audit log tối thiểu (uid / pin / time / IP) để chứng ai từng lấy bản sạch.
5. Chuột phải / save chỉ lấy preview — chấp nhận; cần bằng chứng trên ảnh + dữ liệu, không DRM.

## Mục tiêu sprint

1. Watermark preview: logo + text cố định brand/`PREVIEW · NOT LICENSED`.  
2. Gate list: thiếu original/preview/hash → không list (thông báo seller).  
3. Strip `original_image` khỏi `PinOut` public.  
4. Audit log mint và/hoặc hit signed original.  
5. Smoke evidence path (unpaid vs paid/owner).

## Ngoài phạm vi

Payout seller · DRM / invisible / per-viewer mark · chặn screenshot · tắt context-menu như AC chính · đổi SePay/order · Admin UI forensics product.
