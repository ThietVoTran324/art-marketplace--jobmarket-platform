# Plan #2 decisions — AI_RAG_Sprint1

**CHỐT** 2026-11-05 — overrides: **T1=A → hướng B**, **T3=C** (default Gemini embed, config đổi được); còn lại **all suggest**.

BR: [business_requirement.md](business_requirement.md) · Trio: [PLANNING_TRIO.md](PLANNING_TRIO.md)

---

## 1. Quiz → CHỐT

| ID | CHỐT | Ghi chú |
|----|------|---------|
| **T1** | **A** seed FAQ md trong repo + reindex | **Hướng bản cuối = B** (Admin CMS / FAQ editable DB) — **nợ** `N-rag-faq-cms` → sprint sau; schema/meta đủ không chặn B |
| T2 | **A** chunk theo heading/section FAQ (~200–500 token, overlap nhỏ) | |
| **T3** | **C** `AI_RAG_EMBED_PROVIDER` | **Default = Gemini embedding API** (chung `AI_GEMINI_API_KEY`); có thể đổi sang Jina (hoặc provider khác) qua config sau — không hardcode một vendor |
| T4 | **A** pgvector trên Postgres app + bảng documents/chunks | |
| T5 | **A** skill chat `retrieve_knowledge` | Không public dump corpus |
| T6 | **A** top_k ≈ 4–6; optional min score; `AI_RAG_*` | |
| T7 | **A** CLI/script `reindex_rag` (+ optional Celery); idempotent content hash | |
| T8 | **A** cite meta (source_id/title/path) + markdown; FE tái dụng Sprint2 | |
| T9 | **A** retrieve trong turn chat hiện có; embed chỉ lúc reindex | |
| T10 | **A** pin text **out code**; schema/`source_type` sẵn mở rộng wave 1.1 | = BR Q2 A→C |
| T11 | **A** Out package dưới đây | |

---

## 2. Architecture sketch

```
FAQ md (git) ──reindex──► chunk ──embed(API)──► Postgres+pgvector
                                                      │
User chat ──tool retrieve_knowledge──► top-k + cite ──┘
SQL skills (listed/orders/pins) không đổi
```

**Bản cuối (nợ):** Admin/CMS ghi FAQ vào DB → cùng pipeline reindex (thay hoặc bổ sung đọc md).

---

## 3. Schema sketch (hướng — tên cột chốt lúc implement)

### Documents / sources
- id, `source_type` (`faq` | sau: `pin`…), `source_key` (ổn định), title, optional path/url  
- `content_hash`, `updated_at`  
- optional: `body` hoặc chỉ trỏ file path cho FAQ md  

### Chunks
- id, document_id, `chunk_index`, `content`, optional heading  
- `embedding` vector (pgvector), `content_hash`  
- meta JSONB (default `{}`)

**Sẵn cho B / 1.1:** `source_type` + `source_key` không gắn chết “chỉ file”.

**Không** bảng summary memory.

---

## 4. API / skill sketch

| Method | Path / tool | Việc |
|--------|-------------|------|
| (internal) | skill `retrieve_knowledge` | `{ query, limit? }` → chunks + cite meta |
| (ops) | script/job reindex | FAQ corpus → chunk → embed → upsert |
| optional | Celery task reindex | Không block request chat |

- Auth chat: login như Sprint2.  
- Không REST public dump toàn bộ FAQ trừ khi Plan sau mở CMS (B).

---

## 5. Config keys (hướng)

| Key | Default gợi ý |
|-----|----------------|
| `AI_RAG_ENABLED` | false → true khi ship |
| `AI_RAG_EMBED_PROVIDER` | `gemini` (đổi `jina` sau) |
| `AI_RAG_EMBED_MODEL` | model id theo provider |
| `AI_RAG_TOP_K` | 5 |
| `AI_RAG_MIN_SCORE` | optional |
| `AI_GEMINI_API_KEY` | dùng khi provider=gemini |
| (sau) `AI_RAG_JINA_API_KEY` | khi bật Jina |

---

## 6. FE

- Tái dụng markdown + cite lite Sprint2.  
- Không FAQ CMS UI trong sprint này (**nợ B**).

---

## 7. Nợ / Out — note sprint sau (bắt buộc giữ)

### 7.1 Nợ đã ghi nhận (làm sau, cùng product line)

| ID | Việc | Khi |
|----|------|-----|
| **N-rag-faq-cms** | FAQ editable (Admin/CMS DB) = hướng **T1 B bản cuối**; reindex từ DB | Sau FAQ md ổn |
| **N-rag-pin-text** | Corpus FAQ + pin text (Plan #1 Q2 → C / wave 1.1) | Sau FAQ 1.0 |
| **N-rag-jd-text** | Embed JD | Sau pin text nếu cần |
| **N-rag-jina-live** | Bật provider Jina trên soft-live (key + prove) | Khi đổi `AI_RAG_EMBED_PROVIDER` |
| **N-rag-admin-reindex-ui** | Nút admin “Reindex RAG” | Cùng hoặc sau CMS |

### 7.2 Out (không làm trong AI_RAG_Sprint1)

| ID | Việc | Đích |
|----|------|------|
| N-summary-memory | Rolling chat summary | Chat sau |
| N-framework | LangChain / LlamaIndex bắt buộc | Chat 2.1 |
| N-router-model | 2-model router | Sau |
| N-self-host-embed | Local sentence-transformers trên VPS 4 GiB | Reject soft-live hiện tại |
| N-multimodal-embed | Image embed | FEED-P4b / sau |
| N-replace-sql-search | Thay search_pins/listed bằng vector | Không |
| N-feed-p4-inject | Inject vector vào home feed | FEED-P4 riêng |
| N-mutate / N-multithread / N-ws | Như chat Out | Giữ |
| N-autotag-chat / N-vision-scan-all / N-open / N-guest-chat | Cấm / không | Giữ |

Đồng bộ: [`../../Planing_docs/deferred_and_out_of_scope_backlog.md`](../../Planing_docs/deferred_and_out_of_scope_backlog.md) §J / §K.

---

## 8. Files chạm (implement sau lệnh)

- `app/ai/rag/` (chunk, embed provider, retrieve, reindex)  
- Migration pgvector + documents/chunks  
- Skill + prompt chat  
- Corpus FAQ md seed  
- Config / `.env.example`  
- Docs checklist  

**Không** FAQ Admin UI (nợ B).
