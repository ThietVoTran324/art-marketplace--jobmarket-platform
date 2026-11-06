# Devplan checklist — AI_RAG_Sprint1

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)  
**BR:** [business_requirement.md](business_requirement.md)

---

## A. Corpus & chunk

- [x] Seed FAQ md trong `app/ai/rag/corpus/`
- [x] Chunk theo heading/section + overlap nhỏ
- [x] Note **N-rag-faq-cms** (hướng T1 B) — chưa CMS UI

## B. Embed & store

- [x] `AI_RAG_EMBED_PROVIDER` (default `gemini`; sẵn đổi Jina)
- [x] Gemini embedding client
- [x] Migration pgvector + documents/chunks (`source_type` sẵn pin)
- [x] Reindex script idempotent (content hash)
- [x] docker-compose postgres → `pgvector/pgvector:pg15`

## C. Chat retrieve

- [x] Skill `retrieve_knowledge` + tool decl + prompt cite
- [x] top_k / min_score config
- [x] Không thay SQL skills Sprint2

## D. Config & ops

- [x] `AI_RAG_*` + `.env.example`
- [x] Celery task `reindex_rag_corpus`
- [x] Prove: migrate + `python -m scripts.reindex_rag` trên local (19 chunks)

## E. Prove-done

- [ ] AC-01…07 BR (manual chat FAQ cite + SQL tools)
- [x] Provider Gemini default OK (`gemini-embedding-001` @ 768)
- [x] Out/nợ §7 plan_mode đã note

## Nợ / Out — không làm sprint này

| Nợ (sau) | Out / cấm |
|----------|-----------|
| N-rag-faq-cms (T1→B) | N-summary-memory · N-framework · N-router-model |
| N-rag-pin-text (1.1) | N-self-host-embed · N-multimodal-embed |
| N-rag-jd-text | N-replace-sql-search · N-feed-p4-inject |
| N-rag-jina-live · N-rag-admin-reindex-ui | N-autotag-chat · N-vision-scan-all · N-open · N-guest-chat |
