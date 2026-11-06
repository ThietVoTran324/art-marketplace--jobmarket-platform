# Giáo án học — AI_Chat_Sprint1 (đã implement)

**Mục tiêu học:** Nắm **AI application backend junior** qua feature chat thật: prompt/guardrail, memory, tool-calling, authz, quota, API, UI.  
**Không phải:** train model / RAG / LangChain (đã note sprint sau).

Đọc kèm: [plan_mode_decisions.md](plan_mode_decisions.md) · [learning path](../../Planing_docs/ai_application_learning_path.md)

---

## 0. Bạn đã “học gì” trước đó?

| Feature trước | Concept |
|---------------|---------|
| Auto-tag pin | 1 ảnh → 1 Gemini call, structured JSON, Celery queue, RPD |

Chatbox **khác**: hội thoại nhiều turn, **tools**, **lưu history**, **phân quyền data**.

---

## 1. Kiến trúc tổng (1 pipeline AI)

```
[Vue AiChatWidget]
    POST/GET /api/ai/chat/messages
        → auth (cookie session → user_id)
        → quota / độ dài input
        → Postgres: conversation + messages
        → Gemini (+ function declarations)
        → skills.py (SQL, authz cứng)
        → lưu assistant + ai_tool_invocations
        → trả reply (sync)
```

**Bằng chứng:**
- FE: `vuejs/src/components/AiChatWidget.vue` + mount `App.vue`
- API: `app/api/rest/ai_chat/routes.py`
- Orchestration: `app/ai/chat/service.py`
- Model+tools: `app/ai/chat/gemini_chat.py`
- Skills: `app/ai/chat/skills.py`
- Schema: migration `b3c4d5e6f7a8_ai_chat_tables.py` + ORM `AiConversationsOrm` / `AiMessagesOrm` / `AiToolInvocationsOrm`

---

## 2. Memory (lịch sử)

| Quyết định | Cách làm | File |
|------------|----------|------|
| 1 user / 1 thread | `ai_conversations.user_id` UNIQUE | models + `ensure_conversation` |
| SSOT messages | `ai_messages` role/content/`meta` **bắt buộc** | migration |
| Gửi model | Chỉ **window** `AI_CHAT_HISTORY_WINDOW` (default 12) | `load_history_window` |
| Không dual summary | Chưa có bảng summary | Plan #2 T5 |

**Học gì:** LLM API **stateless** — mỗi turn bạn **tự gửi lại** history (cắt cửa sổ). Đó là memory phía app, không phải “não” Gemini giữ session.

**Thử:** Chat 2–3 câu → refresh trang → `GET /api/ai/chat/messages` vẫn còn.

---

## 3. Soft-closed + soft

| Lớp | Cơ chế | Bằng chứng |
|-----|--------|-----------|
| Prompt | System: chỉ domain web; từ chối lạc đề | `app/ai/chat/prompts.py` |
| Heuristic nhẹ | Keyword toán/bài tập **và** không có từ product → trả hint, **không gọi** Gemini | `_looks_offtopic` trong `service.py` |
| Quota | Đếm user messages từ 00:00 UTC | `count_user_turns_today` + `AI_CHAT_MAX_TURNS_PER_DAY` |
| Output | `max_output_tokens` | `AI_CHAT_MAX_OUTPUT_TOKENS` |

**Học gì:** Cost control = **ít call vô ích** + **ít token**, không chỉ “model thông minh”.

---

## 4. Tool / function calling (skills)

Gemini nhận **function declarations** → có thể trả `function_call` → backend chạy skill → gửi `function_response` → model trả lời text.

| Skill | Data | Authz |
|-------|------|--------|
| `search_pins` | Pin public (title/desc) | Không đụng private |
| `pin_engagement_summary` | likes/saves/views + first liker username | Theo `pin_id` public |
| `search_job_posts` | JD `active` + company active | Public |
| `my_marketplace_and_jobs_summary` | Orders + applications | **`user_id` chỉ từ session** |

**Cấm:** auto-tag / retag — không có trong `ALLOWED_TOOLS`.

**Bằng chứng authz:** `skill_my_activity(..., user_id=user_id)` — argument model **bị bỏ** (`_ = arguments`).

**Học gì:** JD “tool calling” = model **chọn** tool; **backend enforce** quyền. Không tin prompt / không tin arg `user_id` từ model.

**Trace:** mỗi lần gọi tool → row `ai_tool_invocations` + `meta.tools` trên assistant message.

---

## 5. Sync vs async

| Sync (trong request) | “Async-side” MVP |
|----------------------|------------------|
| Gemini + skills + persist + HTTP reply | `logger.info("ai_chat_metrics ...")` sau turn |

Celery enrich đầy đủ = có thể thêm sau; Plan cho phép async log/token không block UX.

---

## 6. Config / bật feature

```env
AI_CHAT_ENABLED=true
AI_GEMINI_API_KEY=...   # dùng chung auto-tag
AI_CHAT_MODEL=gemini-flash-lite-latest
AI_CHAT_MAX_TURNS_PER_DAY=30
AI_CHAT_HISTORY_WINDOW=12
AI_CHAT_MAX_INPUT_CHARS=2000
AI_CHAT_MAX_OUTPUT_TOKENS=512
```

`app/config.py` + `.env.example`.

---

## 7. UI

- FAB góc phải dưới, mọi page (trừ portfolio).
- Guest mở panel → login modal.
- Login: load history + gửi tin.

**Bằng chứng:** `AiChatWidget.vue`.

---

## 8. Việc cố ý CHƯA làm (học sau)

| Note | Topic học |
|------|-----------|
| N-stream (SSE) | Streaming tokens |
| N-rag | Embeddings + retrieve |
| N-framework | LangChain / LangGraph |
| N-router-model | 2 tầng model |
| N-summary-memory | Rolling summary |
| N-mutate | Tool ghi DB |

---

## 9. Bài tập tự kiểm (sau khi bật `AI_CHAT_ENABLED`)

1. Login → mở AI → hỏi *“giải phương trình bậc 2”* → expect từ chối ngắn (heuristic hoặc prompt).  
2. Hỏi *“tìm pin về landscape”* → expect tool `search_pins` (xem `ai_tool_invocations` hoặc meta).  
3. Hỏi *“đơn hàng / apply gần đây của tôi”* → `my_marketplace_and_jobs_summary`.  
4. User B không thấy orders của user A.  
5. Vượt 30 turn/ngày → `quota_exceeded`.  
6. Auto-tag pin vẫn chạy riêng; chat **không** có tool retag.

---

## 10. Map JD junior ↔ chỗ trong code

| JD keyword | Chỗ nhìn |
|------------|----------|
| Prompt engineering | `prompts.py` |
| LLM API integration | `gemini_chat.py` |
| Function/tool calling | declarations + `dispatch_skill` |
| RAG | *(chưa — N-rag)* |
| LangChain | *(chưa — N-framework)* |
| Memory | `ai_messages` + window |
| Authz / security | session `user_id` + ALLOWED_TOOLS |
| FastAPI + SQLAlchemy | routes + skills |
| Cost / rate limit | quota + offtopic skip + max tokens |

Hết Sprint1 bạn có thể giải thích end-to-end trong phỏng vấn: *“Tôi build soft-closed assistant với Postgres memory và Gemini native tools, authz trên skill layer…”*
