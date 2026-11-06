# AI RAG — follow-ups / đề xuất (sau FAQ MVP)

> Cập nhật 2026-11-06. Không phải Plan #1 CHỐT.  
> Backlog SSOT mirror: [`../../Planing_docs/deferred_and_out_of_scope_backlog.md`](../../Planing_docs/deferred_and_out_of_scope_backlog.md) §K.

## Chuẩn bị làm — nhóm A (**CHỐT scope 2026-11-06**)

| # | ID | Việc | Trong Plan A? |
|---|-----|------|----------------|
| 1 | N-rag-pin-text | Embed pin title/description/tags | **IN** → Sprint1.1 Plan #1 CHỐT |
| 2 | N-rag-hybrid-rrf | Hybrid vector + keyword → **RRF** | **IN** |
| 3 | N-rag-semantic-parent-child | Semantic chunking + parent–child retrieve | **IN** |
| 3b | N-rag-intent-tags | Intent→English tags→catalog embed-match→SQL (read-only) | **IN** (CHỐT 2026-11-06; không retag) |
| 4 | N-rag-faq-cms | FAQ CMS/DB (hướng T1 B) | Sau A / song song nếu tách |
| 5 | N-rag-admin-reindex-ui | Admin reindex | Sau / cùng CMS |
| 6 | N-rag-jina-live | Provider Jina soft-live | Sau |
| 7 | N-rag-jd-text | Embed JD | Sau pin-text |

**Plan #1 tiếp theo:** `AI_RAG_Sprint1.1` = pin-text + semantic/parent-child + hybrid RRF.  
**Vẫn Out A:** Vision-LLM/OCR bảng+caption (`AI-N-rag-doc-vision-ocr`).

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
