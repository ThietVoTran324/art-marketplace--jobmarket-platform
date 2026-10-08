# Home feed personalization — CHỐT hướng (2026-10-08)

> **Scope:** Home feed (`GET /api/pins/` hiện = timeline `id` desc, giống nhau mọi account).  
> **VPS soft-live:** ~4 GiB RAM, **0 swap** → không self-host embedding model.  
> **Trạng thái:** Plan #1+#2 **CHỐT**; implement **IN PROGRESS** → [`../Implement_docs/Feed_Sprint1/`](../Implement_docs/Feed_Sprint1/).

---

## In scope — làm trước (P0 → P3)

| Phase | Ship | Ghi chú |
|-------|------|---------|
| **P0** | Home blend: following mới · tag affinity (like/save/view) · explore/trending; seed theo `user_id` + ngày | Guest: trending + shuffle có seed theo ngày |
| **P1** | Đưa recommendation tag-based hiện có vào feed (không chỉ Aside Updates); exclude đã xem/save gần đây | Tận dụng Celery `make_user_recommendations` / `users_view_pins` |
| **P2** | Diversity: không >2–3 pin liên tiếp cùng author/tag; inject fresh + popular 7d | Rule trong ranker |
| **P3** | Signal weights: save > like > dwell/view; cold-start rõ | Guest vs logged-in paths |

**Opt-out:** tag “Everything” / mode timeline cũ giữ được (không bắt mọi client chỉ personalized).

**Out of P0–P3:** embedding model, heavy CF matrix, Firebase phụ, 3rd-party recommend SaaS bắt buộc.

---

## Deferred — P4 (note, không làm trong P0–P3)

| ID | Mục | Điều kiện mở lại |
|----|-----|------------------|
| **FEED-P4** | Embedding / lookalike qua **API 3rd party** (ứng viên: **Jina** Embeddings free key ~100 RPM / 100K TPM; `jina-embeddings-v5-text-nano` ưu tiên text title+desc+tags) → lưu vector hoặc top‑K neighbors trong **Postgres** (không bắt buộc Firebase) → inject một phần vào feed | Sau khi P0–P3 ổn định; chấp nhận quota/token; VPS vẫn không self-host 239M/677M |
| FEED-P4b | Multimodal / image embedding (visual similarity) | Khi text-only không đủ; review cost + privacy ảnh |
| FEED-P4c | Self-host / heavy CF in-process trên VPS | **Reject** trên máy ~4 GiB / 0 swap; cần RAM ≥ ~8 GiB hoặc worker tách |

Chi tiết backlog: [`deferred_and_out_of_scope_backlog.md`](deferred_and_out_of_scope_backlog.md) §I.

---

## Pipeline (CHỐT Plan #1 · AC-05)

```
Candidate pools: Following · Tag affinity · Explore · Trending · Fresh
  → Deduplicate → Ranker → Diversity → Feed
```

Weights tương tác (AC-18): tập trung một config; tương đối save=3 · like=2 · view=1 (hằng số Plan #2).

## Next

1. Plan #2 quiz (route, pool ratios, N diversity, chrono query).  
2. Implement sau Plan #2 CHỐT.  
3. Không pull FEED-P4 vào cùng sprint.
