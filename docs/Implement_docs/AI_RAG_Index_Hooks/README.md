# AI_RAG_Index_Hooks — phase A (enqueue 1 pin / 1 tag)

**Status:** Plan #1+#2 **CHỐT** · Implement + Prove **DONE** 2026-11-15  
**Prereq:** [`../AI_RAG_Index_Automation/`](../AI_RAG_Index_Automation/) (phase B) · FAQ CMS · Celery `ai_auto_tag`.

## Scope

Hook async: pin create / tag attach / sau auto-tag success; tag mới; xóa pin → gỡ RAG.  
Beat missing daily (**B**) giữ safety net.

## Ops

| Key | Default | Ghi chú |
|-----|---------|---------|
| `AI_RAG_HOOK_ENABLED` | `false` | **Prod/local test:** `true` + restart api + worker-ai |

Call-sites: `POST /pins/`, `POST /pins/create-pin-entity`, `DELETE /pins/{id}`, `POST /tags/`, `run_auto_tag` success.  
Tasks: `reindex_rag_pin` / `reindex_rag_tag` / `remove_rag_pin` → queue `ai_auto_tag`.  
Rename tag: helper `enqueue_rag_tag_rename` sẵn — wire khi có API.

## Docs

| File | Vai trò |
|------|---------|
| [business_requirement.md](business_requirement.md) | Plan #1 |
| [plan_mode_decisions.md](plan_mode_decisions.md) | Plan #2 |
| [devplan_checklist.md](devplan_checklist.md) | Implement + prove |
| [PLANNING_TRIO.md](PLANNING_TRIO.md) | Gate |
