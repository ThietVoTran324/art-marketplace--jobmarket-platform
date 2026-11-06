# Plan #2 decisions — AI_Chat_Sprint2

**CHỐT** 2026-11-04 — overrides: **T1=C**, **T2=C + thumb** (collection = ảnh đầu / cover), **T3–T8=A**, job link **mở tab mới**, còn lại **all suggest**.

BR: [business_requirement.md](business_requirement.md) · Trio: [PLANNING_TRIO.md](PLANNING_TRIO.md)

---

## 1. Quiz → CHỐT

| ID | CHỐT | Ghi chú |
|----|------|---------|
| **T1** | **C** — skill mới `search_listed_pins` **và** flag `listed_only` trên `search_pins` | Discovery “đang bán” + search chung có filter |
| **T2** | **C** — cite **absolute URL** (`FRONTEND_DOMAIN` + path) **+ hình nhỏ** | Collection / multi-image: **ảnh đầu** (`sort_order` 0 / cover `pins.image`) |
| T3 | **A** — prompt bắt markdown cite; cấm bịa id/url | Không service rewrite link |
| T4 | **A** — nới prompt tư vấn art; heuristic offtopic giữ hướng Sprint1 | Không open ChatGPT |
| T5 | **A** — `POST …/messages/stream` SSE; giữ POST JSON fallback | AC-06 |
| T6 | **A** — events: `meta` → `token`* → `done`/`error`; tool xong rồi mới stream text | |
| T7 | **A** — `DELETE /api/ai/chat/conversation` clear 1 thread | Xóa messages + tool_invocations |
| T8 | **A** (+ override UX) — markdown links tối thiểu **và** **thumb + title** cho pin | Không full rich marketplace card (`N-rich-pin-card` vẫn out) |
| T9 | **A** — SSE bubble lớn dần; lỗi → fallback POST JSON | |
| T10 | **A** — nút clear + confirm trong panel | |
| T11 | **A** — không bảng mới; clear = delete rows | |
| T12 | **A** — `AI_CHAT_SSE_ENABLED`; dùng sẵn `FRONTEND_DOMAIN` cho absolute cite/thumb origin | |
| T13 | **A** — default limit 5, max 10 | |
| T14 | **A** + **job override** — pin/user/JD có absolute `url`; **job** FE `target=_blank` / `window.open` | Route: `/pin/:id`, `/user/:username`, `/jobs/:id` |
| T15 | **A** — Out BR §6 giữ nguyên; cấm retag / vision-scan-all | |

**Refine Plan #1 S2-16:** Sprint2 cite **bắt buộc absolute `url`** (T2 C); `path` relative vẫn trả kèm để FE/router nếu cần.

---

## 2. Skill / payload sketch (không phải migration)

### Tools

| Tool | Thay đổi |
|------|----------|
| `search_pins` | + `listed_only: bool`; result mỗi pin: `id`, `title`, `author`, `path`, **`url`**, **`thumb_url`**, optional `listed`/price nếu có |
| `search_listed_pins` | **Mới** — `artist_username?`, `query?`, `limit?`; chỉ listing `listed` + giá public |
| `pin_engagement_summary` | + `path`/`url`/`thumb_url` |
| `search_job_posts` | + `path`/`url` (absolute); **không** bắt buộc thumb |
| `my_marketplace_and_jobs_summary` | Orders/apps: `url` khi có deep-link public/an toàn; không lộ private người khác |

### Absolute URL

- Origin: `settings.FRONTEND_DOMAIN.rstrip("/")`
- Pin page: `{origin}/pin/{id}`
- User: `{origin}/user/{username}`
- Job: `{origin}/jobs/{id}`
- Thumb (preview watermarked): `{origin}/api/pins/upload/{id}`  
  (cùng origin qua Vite proxy / soft-live; **cover = ảnh đầu** collection — `pins.image` / `pin_images.sort_order=0`)

### Thumb rule

| Case | `thumb_url` |
|------|-------------|
| Pin 1 ảnh | Cover / `pins.image` → `/api/pins/upload/{id}` |
| Pin collection | **Ảnh đầu** (sort_order 0), không gallery trong chat |
| Không có ảnh | Bỏ `thumb_url` hoặc default placeholder URL đã có sẵn API |

---

## 3. API sketch

| Method | Path | Việc |
|--------|------|------|
| POST | `/api/ai/chat/messages` | Giữ JSON sync (fallback) |
| POST | `/api/ai/chat/messages/stream` | SSE turn (`AI_CHAT_SSE_ENABLED`) |
| GET | `/api/ai/chat/messages` | History |
| DELETE | `/api/ai/chat/conversation` | Clear messages + tool rows của caller |

**SSE events (T6):** `meta` (conversation/message ids) → `token` (delta text) → `done` (full assistant + ids) | `error`.

Auth: login required (giữ Sprint1).

---

## 4. Runtime

**Sync JSON / SSE core (giống Sprint1 + stream):**  
auth → quota → ensure conv → persist user → window history → Gemini + tools (listed / search) → persist assistant →  
- JSON: return full  
- SSE: stream assistant text sau tool loop  

**Clear:** delete `ai_messages` + `ai_tool_invocations` theo `conversation_id` của caller; optional touch `updated_at`.

**Cấm:** enqueue auto-tag; vision-scan catalog; LangChain.

---

## 5. Config

| Key | Default / ghi chú |
|-----|-------------------|
| `AI_CHAT_SSE_ENABLED` | false → true khi ship stream |
| `FRONTEND_DOMAIN` | **đã có** — absolute cite + thumb origin |
| Các `AI_CHAT_*` Sprint1 | Giữ |

Không bắt buộc `AI_CHAT_FRONTEND_ORIGIN` riêng nếu trùng `FRONTEND_DOMAIN`.

---

## 6. FE (`AiChatWidget.vue`)

1. Markdown links tối thiểu (`[text](url)`).  
2. **Pin cite lite:** nếu tool/meta hoặc parse được pin → **img nhỏ (`thumb_url`) + title link** (`url`, cùng tab SPA `router.push` **hoặc** `<a href>` nội bộ).  
3. **Job link:** luôn **mở page/tab mới** (`target="_blank"` + `rel="noopener"`).  
4. SSE typing-token; fallback POST JSON.  
5. Nút **Xóa hội thoại** + confirm → `DELETE conversation`.

**Out FE:** full pin marketplace card / gallery collection trong bubble (`N-rich-pin-card`).

---

## 7. Prompt

- Soft-closed **nới art** (T4).  
- Khi skill trả `url`/`thumb_url`: cite markdown absolute; nhắc user có thể mở job link.  
- Không bịa pin/job id/url.  
- Không nhận lệnh retag / dump DB.

---

## 8. Out of scope + cấm (không sót — khớp BR §6)

| ID | Việc | Khi |
|----|------|-----|
| N-framework | LangChain / LangGraph | Sprint2.1 |
| N-router-model | 2-model router | Sau |
| N-rag | Embed / vector | AI_RAG_Sprint |
| N-summary-memory | Rolling summary | Sau |
| N-vision-rerank-small-N | Vision top-N | Sau |
| N-mutate | Mutate qua bot | Sau |
| N-mongo-ctx | Mongo staging | Nếu cần |
| N-multithread | Multi-thread | Sau |
| N-msg-edit-delete | Xóa/sửa từng message | Chỉ clear-all |
| N-cache-prefix | Gemini cache | Cost sau |
| N-ws | WebSocket | Sau SSE |
| N-rich-pin-card | Card pin đầy đủ / gallery | **Out** — Sprint2 chỉ thumb nhỏ |
| N-guest-discovery | Guest chat public | Không |
| N-autotag-chat | Chat retag | **Cấm** |
| N-vision-scan-all | Vision cả kho | **Cấm** |
| N-open | Open ChatGPT | **Không** |
| N-guest-chat | Guest full chat | **Không** |

---

## 9. Files chạm (implement sau lệnh)

- `app/ai/chat/skills.py`, `gemini_chat.py`, `prompts*`, `service.py`  
- `app/api/rest/ai_chat/` (+ stream + DELETE)  
- `vuejs/src/components/AiChatWidget.vue`  
- Config / `.env.example` (`AI_CHAT_SSE_ENABLED`)  
- Docs checklist / LEARNING sync nhẹ  

**Không** migration bảng mới (T11 A).
