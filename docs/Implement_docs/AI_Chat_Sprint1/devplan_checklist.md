# Devplan checklist — AI_Chat_Sprint1

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)  
**Giáo án:** [LESSON_AI_CHAT.md](LESSON_AI_CHAT.md)

---

## A. Data & config

- [x] Migration `b3c4d5e6f7a8` — conversations / messages / tool_invocations
- [x] ORM models
- [x] Settings `AI_CHAT_*` + `.env.example`
- [x] Feature flag `AI_CHAT_ENABLED`

## B. AI chat core

- [x] `app/ai/chat/` prompts, gemini tools, skills, service
- [x] Native function calling + tool loop
- [x] Skills ×4 + authz session
- [x] Cấm auto-tag trong ALLOWED_TOOLS
- [x] Quota + input/output limits
- [x] Persist + tool_invocations
- [x] Metrics log (async-side lite)
- [x] 429 / provider friendly message

## C. API

- [x] `POST /api/ai/chat/messages`
- [x] `GET /api/ai/chat/messages`
- [x] Login required; mount router

## D. FE

- [x] `AiChatWidget.vue` global FAB
- [x] Guest → login
- [x] History + send

## E. Prove-done (manual trên env đã bật)

- [ ] AC-01…10 theo LESSON §9
- [ ] migrate upgrade head trên local/prod

## F. Docs

- [x] LESSON_AI_CHAT.md
- [x] Out-notes trong plan_mode §8

## Out — không làm Sprint1

N-stream (SSE) · N-rag · N-framework · N-router-model · N-summary-memory · N-mutate · N-mongo-ctx · N-multithread · N-cache-prefix · N-ws · N-msg-delete · N-autotag-chat (cấm)
