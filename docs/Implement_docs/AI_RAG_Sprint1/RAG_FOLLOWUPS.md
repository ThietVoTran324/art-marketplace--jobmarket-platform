# AI RAG — follow-ups / đề xuất (sau FAQ MVP)

> Cập nhật 2026-11-14.  
> Backlog SSOT mirror: [`../../Planing_docs/deferred_and_out_of_scope_backlog.md`](../../Planing_docs/deferred_and_out_of_scope_backlog.md) §K.

## Chuẩn bị làm — nhóm A (**CHỐT scope 2026-11-06**) — DONE code

| # | ID | Việc | Trong Plan A? |
|---|-----|------|----------------|
| 1 | N-rag-pin-text | Embed pin title/description/tags | **DONE** Sprint1.1 |
| 2 | N-rag-hybrid-rrf | Hybrid vector + keyword → **RRF** | **DONE** |
| 3 | N-rag-semantic-parent-child | Semantic chunking + parent–child retrieve | **DONE** |
| 3b | N-rag-intent-tags | Intent→English tags→catalog embed-match→SQL (read-only) | **DONE** |
| 4 | N-rag-faq-cms | FAQ CMS/DB (hướng T1 B) | **pulled → AI_RAG_FAQ_CMS** |
| 5 | N-rag-admin-reindex-ui | Admin reindex pins/tags UI | Sau (FAQ nút đã có trong CMS) |
| 6 | N-rag-jina-live | Provider Jina soft-live | Sau |
| 7 | N-rag-jd-text | Embed JD | Sau |

## Pin/tag index vào RAG — **CHỐT hướng 2026-11-14**

**Hiện trạng:** pin/tag RAG **chỉ** qua CLI/`reindex_rag` (ops tay). Pin create chỉ queue **auto-tag**, không embed RAG. FAQ CMS đã là luồng chính (publish → Celery).

**CHỐT lộ trình (không để mãi phụ thuộc tool tay):**

| Phase | Hướng | Việc |
|-------|--------|------|
| **1** | **B — daily/scheduled** | **DONE** — `AI_RAG_Index_Automation` (prove 2026-11-15) |
| **2 (hiện tại)** | **A — luồng chính (hook)** | `AI_RAG_Index_Hooks` — Plan #1 **CHỐT** 2026-11-15: create/update + sau auto-tag → 1 pin; tag mới/đổi tên → 1 tag; xóa pin → gỡ RAG; **B giữ safety net** |

**VPS:** OK nếu **async + queue + throttle**; **cấm** embed sync trong HTTP.  
**Không:** chỉ A không có B; A sync trong request.

**Sprint A:** [`../AI_RAG_Index_Hooks/`](../AI_RAG_Index_Hooks/) — Plan #1+#2 CHỐT; implement + prove **DONE** 2026-11-15.

## Đề xuất kỹ thuật — đánh giá (user 2026-11-06) → chốt

### 1) Vision-LLM / OCR — bảng + caption ảnh khi parse

| | |
|--|--|
| Kết luận | **Out Plan A** — defer khi ingest PDF/doc layout |

### 2) Semantic + Parent–Child chunking

| | |
|--|--|
| Kết luận | **IN Plan A** (CHỐT 2026-11-06) — áp dụng corpus pin (+ refine FAQ nếu cần) |

### 3) Hybrid search (vector + keyword) + RRF

| | |
|--|--|
| Kết luận | **IN Plan A** (CHỐT 2026-11-06) |

## Không nhầm với

- `search_pins` SQL — giữ; hybrid RAG **bổ sung**, không thay listed/orders.  
- Vision-scan-all catalog — **cấm**.  
- FEED-P4 inject feed — stream riêng.
