# Plan #2 decisions — AI_RAG_Index_Hooks

**CHỐT** 2026-11-15 — **all suggest** (T1–T10 = A).  
**Plan #1:** [business_requirement.md](business_requirement.md)

## 1. Quiz → CHỐT

| ID | CHỐT |
|----|------|
| T1 | **A** Task `reindex_rag_pin(pin_id)` |
| T2 | **A** Task `reindex_rag_tag(tag_id)` |
| T3 | **A** Enqueue pin sau create (không chỉ trong auto-tag) |
| T4 | **A** Enqueue pin cuối `run_auto_tag` khi success |
| T5 | **A** `create_tags_on_pin`: tag mới → tag task; mọi attach → pin task |
| T6 | **A** Helper rename sẵn; wire khi có rename API |
| T7 | **A** Task `remove_rag_pin(pin_id)` async sau delete |
| T8 | **A** `delay` thẳng; hash skip trong reindex |
| T9 | **A** `AI_RAG_HOOK_ENABLED` (+ reuse embed throttle) |
| T10 | **A** Queue `ai_auto_tag` |

## 2. Config

| Key | Default | Ý nghĩa |
|-----|---------|---------|
| `AI_RAG_HOOK_ENABLED` | `false` | Opt-in enqueue hooks |

## 3. Sketch

- `_enqueue_rag_pin` / `_enqueue_rag_tag` / `_enqueue_remove_rag_pin` — no-op nếu flag off  
- Tasks trên `ai_auto_tag`  
- Wire: pin create (+ entity), pin delete, `create_tags_on_pin`, `run_auto_tag` done  
- Beat B / CLI không đổi  

## 4. Out

Admin UI · JD · Jina · Vision · đổi Beat · sync embed · Redis debounce  
