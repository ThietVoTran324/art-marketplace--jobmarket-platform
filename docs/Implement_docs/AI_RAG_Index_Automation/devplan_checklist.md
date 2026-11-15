# Devplan checklist — AI_RAG_Index_Automation

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)

## A. Core

- [x] Config `AI_RAG_AUTO_*`
- [x] `missing_only` pins + tags trong reindex
- [x] Task `reindex_rag_missing` + Beat 02:00 UTC
- [x] Route queue `ai_auto_tag`
- [x] CLI `--missing-only` / `--auto-missing`

## B. Docs / ops

- [x] README prod: bật `AI_RAG_AUTO_ENABLED=true`
- [x] Phase A hook = roadmap only

## C. Prove (end sprint)

- [x] Local: dry-run `--auto-missing` (2026-11-15; 0 missing khi đã full)
- [x] Sau run: pin_docs / tag_emb tăng (xóa 1→2/20 rồi reindex → 3/21; upserted pin=1 tag=1)
- [x] Disabled → no-op (`AI_RAG_AUTO_ENABLED=false` → `skipped`)
- [x] Chat regress smoke (FAQ retrieve_knowledge ok; pin cites ok)
