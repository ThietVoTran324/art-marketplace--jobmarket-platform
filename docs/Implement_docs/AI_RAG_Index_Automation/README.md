# AI_RAG_Index_Automation — scheduled pin/tag RAG index

**Status:** Plan #1+#2 **CHỐT** · Implement **DONE** 2026-11-14 · Prove **DONE** 2026-11-15  
**Prereq:** [`../AI_RAG_Sprint1.1/`](../AI_RAG_Sprint1.1/), [`../AI_RAG_FAQ_CMS/`](../AI_RAG_FAQ_CMS/).

## Scope (sprint này)

Celery Beat daily **02:00 UTC**: reindex **missing** pins rồi tags; limit/pause free-tier; CLI fallback.  
Phase A hook = roadmap only (không code sprint này).

## Ops

| Key | Default | Ghi chú |
|-----|---------|---------|
| `AI_RAG_AUTO_ENABLED` | `false` | **Prod:** set `true` + restart beat/worker-ai |
| `AI_RAG_AUTO_PIN_LIMIT` | `50` | Max missing pins / run |
| `AI_RAG_AUTO_TAG_LIMIT` | `200` | Max missing/stale tags / run |

```bash
# Manual (same logic as Beat)
python -m scripts.reindex_rag --auto-missing --dry-run
python -m scripts.reindex_rag --pins --missing-only --limit 50
python -m scripts.reindex_rag --tags --missing-only --limit 200
```

Worker: queue `ai_auto_tag` (celery-worker-ai). Beat entry: `rag-reindex-missing`.

## Docs

| File | Vai trò |
|------|---------|
| [business_requirement.md](business_requirement.md) | Plan #1 |
| [plan_mode_decisions.md](plan_mode_decisions.md) | Plan #2 |
| [devplan_checklist.md](devplan_checklist.md) | Implement + prove |
| [PLANNING_TRIO.md](PLANNING_TRIO.md) | Gate |
