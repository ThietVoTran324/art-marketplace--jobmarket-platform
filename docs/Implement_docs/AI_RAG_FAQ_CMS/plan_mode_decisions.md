# Plan #2 decisions — AI_RAG_FAQ_CMS

**CHỐT** 2026-11-13 — **all suggest** (T1–T8 = A).  
**Plan #1:** [business_requirement.md](business_requirement.md)

## 1. Quiz → CHỐT

| ID | CHỐT | Ghi chú |
|----|------|---------|
| T1 | **A** Bảng CMS FAQ riêng → reindex ghi `ai_rag_documents` | Draft không vào vector |
| T2 | **A** Celery task reindex 1 FAQ | Không block HTTP |
| T3 | **A** Script seed md → CMS idempotent theo slug | |
| T4 | **A** REST admin-only | Prefix `/admin/faq` |
| T5 | **A** Body Markdown | Chunker hiện có |
| T6 | **A** Slug ổn định = `source_key` / cite `faq:{slug}` | |
| T7 | **A** Unpublish → gỡ doc+chunks FAQ đó | |
| T8 | **A** Nút Reindex all FAQ → Celery `mode=faq` | |

## 2. Schema sketch

### `faq_articles` (CMS)
- id, slug (unique), title, body (markdown), status (`draft` | `published`), timestamps  
- Optional: archived via status or `published` toggle only (unpublish = draft)

### Index path
- Publish / reindex-one → upsert `ai_rag_documents` (`source_type=faq`, `source_key=slug`) + chunks  
- Unpublish → delete matching faq document (cascade chunks)  
- Reindex all FAQ → mọi bài `published`; prune stale faq docs không còn published

### Seed
- `python -m scripts.seed_faq_cms_from_corpus` — đọc `app/ai/rag/corpus/*.md`, upsert theo slug=stem, default **published**

## 3. API sketch

| Method | Path | Việc |
|--------|------|------|
| GET | `/admin/faq` | List (admin) |
| POST | `/admin/faq` | Create draft/published |
| GET | `/admin/faq/{id}` | Detail |
| PATCH | `/admin/faq/{id}` | Update fields / status |
| POST | `/admin/faq/{id}/reindex` | Enqueue reindex 1 |
| POST | `/admin/faq/reindex-all` | Enqueue reindex all FAQ |

Auth: `require_roles("admin")`.

## 4. UI

- `/admin/faq` + AdminNav  
- List + form markdown; Publish / Unpublish; Reindex one / all  

## 5. Out

`/help` public · pins/tags reindex UI · JD · Jina · i18n 2 bản bắt buộc  

## 6. Files

- Migration + `FaqArticlesOrm`  
- `app/ai/rag/reindex.py` CMS path  
- `app/ai/tasks.py` reindex one FAQ  
- `app/api/rest/admin` FAQ routes  
- `scripts/seed_faq_cms_from_corpus.py`  
- Vue Admin FAQ view + i18n  
