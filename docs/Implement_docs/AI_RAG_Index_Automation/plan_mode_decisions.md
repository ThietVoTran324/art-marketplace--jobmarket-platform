# Plan #2 decisions — AI_RAG_Index_Automation

**CHỐT** 2026-11-14 — **all suggest** (T1–T8 = A).  
**Plan #1:** [business_requirement.md](business_requirement.md)

## 1. Quiz → CHỐT

| ID | CHỐT |
|----|------|
| T1 | **A** Celery Beat crontab |
| T2 | **A** Một task sequential pins→tags |
| T3 | **A** 02:00 UTC |
| T4 | **A** Pins missing doc only |
| T5 | **A** Tags missing row / hash lệch / embedding null |
| T6 | **A** `AI_RAG_AUTO_*` config |
| T7 | **A** Queue `ai_auto_tag` (worker-ai) |
| T8 | **A** CLI `--missing-only` cùng logic |

## 2. Config

| Key | Default | Ý nghĩa |
|-----|---------|---------|
| `AI_RAG_AUTO_ENABLED` | `false` | Bật Beat job (prod opt-in) |
| `AI_RAG_AUTO_PIN_LIMIT` | `50` | Max missing pins / run |
| `AI_RAG_AUTO_TAG_LIMIT` | `200` | Max missing/stale tags / run |

Tái dùng `AI_RAG_REINDEX_BATCH_*` / `AI_RAG_EMBED_RPM`.

## 3. Sketch

- Beat `rag-reindex-missing` → `reindex_rag_missing` @ 02:00 UTC  
- Task no-op nếu `AI_RAG_AUTO_ENABLED=false`  
- `reindex_pins(..., missing_only=True)` / `reindex_tag_embeddings(..., missing_only=True)`  
- CLI: `python -m scripts.reindex_rag --pins --missing-only --limit 50`  

## 4. Out

Phase A hook · Admin UI · Full refresh daily  
