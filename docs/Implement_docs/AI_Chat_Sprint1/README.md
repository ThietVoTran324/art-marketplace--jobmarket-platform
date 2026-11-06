# AI_Chat_Sprint1 — Platform AI chatbox (MVP)

**Status:** Plan #1/#2 **CHỐT** · Implement **CODED** (prove-done manual khi bật flag)  
**Learning:** [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)  
**Giáo án:** [LESSON_AI_CHAT.md](LESSON_AI_CHAT.md)

## Docs

| File | Role |
|------|------|
| [business_requirement.md](business_requirement.md) | Business |
| [plan_mode_decisions.md](plan_mode_decisions.md) | Technical CHỐT |
| [devplan_checklist.md](devplan_checklist.md) | Tick + prove-done |
| [LESSON_AI_CHAT.md](LESSON_AI_CHAT.md) | Học: đã làm gì / dùng gì / bằng chứng |

## Bật nhanh (local/prod)

```bash
# .env
AI_CHAT_ENABLED=true
# AI_GEMINI_API_KEY=...

alembic upgrade head   # hoặc docker compose exec fastapi-app alembic upgrade head
# recreate fastapi (+ rebuild vue nếu prod bake static)
```

## Out / học sau (không sót)

→ Gom đủ vào Sprint2 draft: [`../AI_Chat_Sprint2/PRELIMINARY_PLAN.md`](../AI_Chat_Sprint2/PRELIMINARY_PLAN.md)

N-cite-links · **N-skill-listed-pins** · N-stream (SSE) · N-framework · N-router-model · N-rag · N-summary-memory · N-mutate · … · N-autotag-chat (**cấm**)
