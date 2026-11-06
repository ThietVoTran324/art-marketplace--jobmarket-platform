# Devplan checklist — AI_RAG_Sprint1.1

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)

## A. Intent → English tags

- [x] Prompt: any language → English kebab-case only; max 4; `[]` nếu rác
- [x] Skill `predict_search_tags` + JSON schema (Gemini)
- [x] Normalize + embed-match catalog + min score config
- [x] **Cấm** ghi pins_tags / gọi auto-tag Celery

## B. Tag catalog embed

- [x] `ai_rag_tag_embeddings`
- [x] Reindex `--tags`

## C. Pin parent–child + hybrid

- [x] Index pin title/desc/tags (`chunk_kind`)
- [x] Parent–child + cite parent url/thumb
- [x] Hybrid keyword + vector → RRF (± matched_tags)
- [x] `reindex_rag --pins`

## D. Chat wire

- [x] Tool decls + prompt
- [ ] Prove-done manual (migrate + reindex tags/pins + chat)

## E. Prove-done

- [ ] VI slang → English tags → matched catalog
- [ ] Paraphrase / exact / RRF
- [ ] Rác → `[]` + fallback
- [ ] Không retag / không index incorrect_tags

## Out

Vision-OCR · CMS · Jina bắt buộc · JD · retag · thay SQL marketplace  
