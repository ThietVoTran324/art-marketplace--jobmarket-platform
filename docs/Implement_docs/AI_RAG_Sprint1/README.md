# AI_RAG_Sprint1 — RAG pipeline (FAQ → chat)

**Status:** Plan #1+#2 CHỐT · **implement DONE** 2026-11-05 — cần migrate pgvector + `reindex_rag`.  
**Prereq:** [`../AI_Chat_Sprint1/`](../AI_Chat_Sprint1/), [`../AI_Chat_Sprint2/`](../AI_Chat_Sprint2/).  
**Learning:** [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)

## Một câu

Chunk → embed (API) → Postgres vector → retrieve + cite trong chat trên **FAQ**; giữ SQL tools; roadmap **FAQ + pin text**.

## Docs

| File | Vai trò |
|------|---------|
| [business_requirement.md](business_requirement.md) | Plan #1 CHỐT + Out §6 |
| [base requirement.md](base%20requirement.md) | Input ngắn |
| [PLANNING_TRIO.md](PLANNING_TRIO.md) | Gate |

## Gate

- [x] Plan #1 CHỐT  
- [x] Plan #2 CHỐT  
- [x] Implement  
- [ ] Prove-done (migrate + reindex + chat FAQ)

**Ops local:**
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
# (image pgvector/pgvector:pg15)
docker compose ... exec fastapi-app alembic upgrade head
docker compose ... exec -w /fastapi -e PYTHONPATH=/fastapi fastapi-app python -m scripts.reindex_rag
```

**Next Plan A (CHỐT):** pin-text + **semantic/parent-child** + **hybrid RRF** — [RAG_FOLLOWUPS.md](RAG_FOLLOWUPS.md) · Planing §K.  
Out A: Vision-OCR. CMS/Jina/JD = sau. 
