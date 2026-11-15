# Devplan checklist — AI_RAG_Index_Hooks

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)

## A. Core

- [x] Config `AI_RAG_HOOK_ENABLED`
- [x] `reindex_rag_pin` / `reindex_rag_tag` / `remove_rag_pin`
- [x] Celery tasks + queue `ai_auto_tag`
- [x] Enqueue helpers (flag gate)
- [x] Wire: pin create, pin delete, tags attach, auto-tag success

## B. Docs / ops

- [x] README + `.env.example`
- [x] Rename helper `enqueue_rag_tag_rename` (no rename API yet)

## C. Prove (end sprint)

- [x] Flag off → no enqueue / tasks `skipped` (2026-11-15)
- [x] Flag on + enqueue pin → doc xuất hiện (pin 4 → doc id 10)
- [x] Attach tag mới → tag_emb + pin reindex (tag 23)
- [x] Delete/remove → RAG doc gone
- [x] Chat smoke (`retrieve_knowledge` ok)
