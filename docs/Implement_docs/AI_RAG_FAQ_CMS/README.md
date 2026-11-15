# AI_RAG_FAQ_CMS — FAQ Admin CMS

**Status:** Plan #1+#2 **CHỐT** 2026-11-13 · **implement DONE** (prove manual còn)  
**Prereq:** [`../AI_RAG_Sprint1/`](../AI_RAG_Sprint1/), [`../AI_RAG_Sprint1.1/`](../AI_RAG_Sprint1.1/), Admin `/admin`.

## Scope

DB SSOT FAQ · draft/publish · admin CRUD · reindex FAQ (bài + all) · seed md một lần.

**Out:** `/help` public · reindex pins/tags UI · JD · Jina bắt buộc · Vision-OCR.

## Docs

| File | Vai trò |
|------|---------|
| [business_requirement.md](business_requirement.md) | Plan #1 |
| [plan_mode_decisions.md](plan_mode_decisions.md) | Plan #2 |
| [devplan_checklist.md](devplan_checklist.md) | Checklist |
| [PLANNING_TRIO.md](PLANNING_TRIO.md) | Gate |

## Ops

```bash
docker exec -w /fastapi fastapi-container alembic upgrade head
docker exec -w /fastapi -e PYTHONPATH=/fastapi fastapi-container \
  python -m scripts.seed_faq_cms_from_corpus
```
