# Devplan checklist — AI_Chat_Sprint2

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)  
**BR:** [business_requirement.md](business_requirement.md)

---

## A. Skills & cite

- [x] `search_listed_pins` (artist/query/limit; chỉ `listed` + giá public)
- [x] `search_pins` + `listed_only`
- [x] Mọi pin result: `path`, absolute `url`, `thumb_url` (collection = cover / ảnh đầu)
- [x] Job result: absolute `url` → `/jobs/{id}`
- [x] User (khi có): absolute `url` → `/user/{username}`
- [x] Prompt: cite markdown absolute; nới art; cấm bịa / retag
- [x] Gemini tool decls cập nhật

## B. API & stream

- [x] `POST /api/ai/chat/messages/stream` SSE (`meta`/`token`/`done`/`error`)
- [x] Giữ `POST /api/ai/chat/messages` JSON fallback
- [x] `DELETE /api/ai/chat/conversation` clear messages + tool_invocations
- [x] `AI_CHAT_SSE_ENABLED` + `.env.example`
- [x] Quota / auth giữ Sprint1

## C. FE

- [x] Markdown links tối thiểu
- [x] Pin cite lite: thumb nhỏ + title link
- [x] Job link: `target="_blank"` + `rel="noopener"`
- [x] SSE token bubble + fallback JSON
- [x] Nút clear + confirm

## D. Prove-done

- [ ] AC-01…10 BR §5 (listed, cite+thumb, index search, private, SSE, clear, no regress)
- [ ] Job mở tab mới
- [ ] Collection pin → thumb = ảnh đầu
- [ ] Không LangChain / RAG / retag / vision-all

## E. Docs

- [x] PLANNING_TRIO gate implement
- [x] Out §8 plan_mode không sót

## Out — không làm Sprint2

N-framework · N-router-model · N-rag · N-summary-memory · N-vision-rerank · N-mutate · N-mongo-ctx · N-multithread · N-msg-edit-delete · N-cache-prefix · N-ws · N-rich-pin-card · N-guest-discovery  
**Cấm:** N-autotag-chat · N-vision-scan-all · N-open · N-guest-chat
