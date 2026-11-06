# Plan #2 decisions — AI_Chat_Sprint1

**CHỐT** 2026-11-03 — `all suggest` technical + overrides: meta JSONB bắt buộc; `ai_tool_invocations` sớm; T5 window+skills (không dual chat-summary); T7 **1 model** (2-model → sprint sau); POST/GET only; sync-core / async-side.

BR: [business_requirement.md](business_requirement.md) · Learning: [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)

---

## 1. Quiz → CHỐT

| ID | CHỐT | Ghi chú |
|----|------|---------|
| T1 | `ai_conversations` (unique `user_id`) + `ai_messages` | `meta` JSONB **NOT NULL** / luôn có (default `{}`) |
| T2 | Bảng `ai_tool_invocations` | Trace sớm, dễ nâng cấp |
| T3 | REST `POST` + `GET` messages only | Không update/delete message Sprint1 |
| T4 | Sync: Gemini + skills + reply; async: log/token/enrich | Không poll Celery cho reply MVP |
| T5 | Full messages SSOT + **history window N**; skill kéo domain khi cần | Không rolling summary song song Sprint1 |
| T6 | Quota config: 30 turn/ngày; input ~2000 chars; output ~512 tokens | `.env` / settings |
| T7 | **1 model** chat + rule/prompt | 2-model router = sprint đầy đủ tiếp theo |
| T8 | Skills: `search_pins`, `pin_engagement_summary`, `search_job_posts`, `my_marketplace_and_jobs_summary` | Gộp “của tôi” một skill |
| T9 | Native Gemini function calling | LangChain = N-framework |
| T10 | `app/ai/chat/` + `app/api/rest/ai_chat/` | Tách auto-tag |
| T11 | Vue global widget (layout), góc phải dưới | Guest → login gate |
| T12 | Chung `AI_GEMINI_API_KEY` + `AI_CHAT_*` | Model mặc định Flash-Lite hướng |
| T13 | Lỗi/429 → message thân thiện; log server | Không retry spam |
| T14 | Engagement: counts + `first_liker` username chỉ nếu public/non-suspended | Không email / internal id |

---

## 2. Schema sketch

### `ai_conversations`
- `id` PK  
- `user_id` UNIQUE FK → users  
- `created_at`, `updated_at`

### `ai_messages`
- `id` PK  
- `conversation_id` FK CASCADE  
- `role` — `user` | `assistant` | `system`  
- `content` text  
- `meta` JSONB **required**, default `{}`  
- `created_at`

### `ai_tool_invocations`
- `id` PK  
- `conversation_id` FK  
- `message_id` FK nullable (assistant message gắn kết quả)  
- `tool_name`  
- `arguments` JSONB  
- `result_summary` JSONB / text (đã redact)  
- `status` — ok | error  
- `created_at`  
- optional: `latency_ms`, `user_id` denorm

**Không** tái sử dụng bảng `messages` người–người.

---

## 3. API sketch

| Method | Path | Việc |
|--------|------|------|
| POST | `/api/ai/chat/messages` | Body `{ content }` → tạo/ensure conversation, persist user msg, chạy turn, persist assistant, return cả hai |
| GET | `/api/ai/chat/messages` | History (limit); chỉ của caller |

- Auth: login required (guest không POST).  
- Skills: internal only (model function-calling → backend).  
- Clear/delete/patch message: **out** Sprint1.

---

## 4. Runtime turn (sync-core / async-side)

**Sync (request):**
1. Auth + quota check + input length  
2. Ensure conversation  
3. Persist user message (`meta={}`)  
4. Load last `AI_CHAT_HISTORY_WINDOW` messages  
5. Gemini (+ tools loop giới hạn bước)  
6. Persist assistant (`meta` có tool refs nếu có) + tool_invocations tối thiểu cần cho AC  
7. Return reply  

**Async (best-effort, sau reply hoặc fire-and-forget):**
- Token usage log / quota reconcile chi tiết  
- Enrich tool rows / metrics  
- Không block UX  

Off-topic: system prompt + optional nhẹ keyword rule — **không** model #2.

---

## 5. Config keys (hướng)

| Key | Default gợi ý |
|-----|----------------|
| `AI_CHAT_ENABLED` | false → true khi ship |
| `AI_CHAT_MODEL` | `gemini-flash-lite-latest` (hoặc alias ổn định) |
| `AI_CHAT_MAX_TURNS_PER_DAY` | 30 |
| `AI_CHAT_HISTORY_WINDOW` | 12 |
| `AI_CHAT_MAX_INPUT_CHARS` | 2000 |
| `AI_CHAT_MAX_OUTPUT_TOKENS` | 512 |
| `AI_GEMINI_API_KEY` | dùng chung auto-tag |

---

## 6. Skills (authz)

| Skill | Data | Authz |
|-------|------|--------|
| `search_pins` | Pin public | Không private pin người khác |
| `pin_engagement_summary` | Counts + optional first public liker | Pin public; không PII nội bộ |
| `search_job_posts` | JD published | Public only |
| `my_marketplace_and_jobs_summary` | Orders + applications caller | `user_id` từ session only |

**Cấm:** auto-tag / retag / admin / mutate.

---

## 7. FE

- Global widget: icon bật/tắt, panel phải dưới, mọi page layout chính.  
- Login: gửi/nhận tin. Guest: CTA login.  
- Không nhúng vào Messages người–người.

---

## 8. Out of scope + note học/làm sau (không sót)

| ID | Việc | Khi |
|----|------|-----|
| N-stream | Stream reply — **ưu tiên SSE** (WS cân nhắc sau) | Sprint UX sau |
| N-rag | Embed + retrieve | AI_RAG / học RAG |
| N-framework | LangChain / LangGraph | Sprint chat đầy đủ tiếp theo |
| N-router-model | Tầng 2 model classifier/router | Cùng sprint đầy đủ tiếp theo (sau 1-model ổn) |
| N-summary-memory | Rolling summary / dual chat context blob | Khi window không đủ |
| N-mutate | Tool ghi + confirm | Sau read-only |
| N-mongo-ctx | Mongo staging context | Chỉ nếu cần |
| N-multithread | Nhiều thread/user | Sau |
| N-cache-prefix | Gemini context cache | Cost optimize |
| N-ws | WebSocket chat transport | Sau REST (+ SSE) |
| N-msg-delete | Xóa/sửa history qua API | Sau |
| N-autotag-chat | Chat gọi retag | **Cấm** |
| N-cite-links | Skill trả `path`/`url` + prompt cite markdown (pin/user/tag) | **Sprint2** — xem [`../AI_Chat_Sprint2/PRELIMINARY_PLAN.md`](../AI_Chat_Sprint2/PRELIMINARY_PLAN.md) |
| N-skill-listed-pins | Tìm pin đang `listed` theo artist/query (public marketplace Q&A) | **Sprint2** |
| N-public-vs-private-matrix | BR: public discovery vs private — tránh né sai câu “đang bán?” | **Sprint2** |
| N-search-via-enriched-index | Skill tìm ảnh dựa tag/index (auto-tag offline); **cấm** vision-scan all pins mỗi câu | **Sprint2** — PRELIMINARY §1.1 |
| N-forbid-vision-scan-all | Hard rule cost | **Sprint2** |

Đồng bộ learning path khi implement xong wave docs.
