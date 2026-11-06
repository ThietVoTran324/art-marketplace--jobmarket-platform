# AI_Chat_Sprint2 — Plan sơ bộ (gom note để khỏi quên)

> **Plan #1 đã CHỐT 2026-11-04** — SSOT: [`business_requirement.md`](business_requirement.md).  
> File này giữ backlog sóng / lịch sử debate; **không** override BR.  
> MVP Sprint1: soft-closed, 1 model, Postgres 1-thread, skills cơ bản, FAB optimistic + typing dots.

---

## 0. Nguyên tắc mang sang Sprint2

1. **Public discovery ≠ private leak** — hỏi “artist X có pin đang bán?” là **public** → skill trả lời; không né bằng “vào marketplace tự xem”.  
2. **Cite có link** = skill trả `path`/`url` + prompt bắt cite; không bịa id.  
3. **Authz vẫn ở skill/backend**; không dump DB; không tin prompt thay gate.  
4. **Auto-tag / retag** = system-only (**cấm** chatbot) — giữ N-autotag-chat.  
5. **Open general assistant / guest full chat** = vẫn **không** (N-open, N-guest-chat).

---

## 1. Việc đã bàn gần đây → candidate Sprint2 (ưu tiên)

| ID | Việc | Ghi chú debate |
|----|------|----------------|
| **N-cite-links** | Skill trả `path` (và optional absolute `FRONTEND_DOMAIN` url); prompt: markdown `[title](path)` cho pin/user/tag | Skill + prompt; **không** service rewrite |
| **N-skill-listed-pins** | Skill (hoặc flag) tìm pin **đang `listed`**, filter theo artist username / query | Trả lời đúng “abc đang rao bán gì?”; kèm price nếu public |
| **N-public-vs-private-matrix** | Viết rõ trong BR: public (listed pins, engagement, JD active) vs private (orders/apps của người khác, payout) | Tránh nhầm soft-closed = cấm mọi marketplace Q&A |
| **N-stream** | Stream token reply — **ưu tiên SSE** | UX đợi dài; WS = N-ws sau nếu cần |
| **N-framework** | LangChain hoặc LangGraph cho orchestration | Học JD; sau khi skill/cite ổn |
| **N-router-model** | Tầng 2: classifier/router model nhẹ trước answer | Cost/off-topic; sau 1-model ổn |
| **N-search-via-enriched-index** | Skill tìm hình (“nhân vật x”) **chỉ query DB** (tag/title/desc ± listed); dựa auto-tag/backfill đã làm giàu — **không** vision-scan cả catalog lúc chat | Xem §1.1 |
| **N-vision-rerank-small-N** (optional) | Sau SQL top-N (vd ≤20) mới hỏi vision “pin nào khớp X?” | Không bắt buộc Sprint2; cấm all-pins |
| **N-forbid-vision-scan-all** | Cấm skill/chat enqueue Gemini vision trên hàng nghìn pin mỗi câu hỏi | Hard rule cost |

### 1.1 Auto-tag ↔ skill tìm ảnh (chốt hướng)

| Đúng | Sai |
|------|-----|
| Auto-tag / backfill **offline** làm giàu tag (+ sau này embed) | Mỗi câu chat gọi vision trên cả kho pin |
| Skill search = SQL/FTS/vector trên **index đã có** | Skill “tìm nhân vật x” = loop `analyze_pin_image` |
| Thiếu tag → trả “chưa thấy trong index” / gợi ý backfill | Đốt RPD để “cứ nhìn hết ảnh” |

Auto-tag **phục vụ** search bằng cách giàu dữ liệu trước; skill **không** thay pipeline auto-tag lúc online.

### Sóng (Plan #1 CHỐT)

| Wave | Nội dung | Trạng thái |
|------|----------|------------|
| **2.A** | N-cite-links + N-skill-listed-pins + matrix + search tag/index | **IN Sprint2** |
| **2.B** | N-stream (SSE) + FE markdown links + clear conversation | **IN Sprint2** |
| **2.C** | N-framework (± N-router-model) | **OUT** → Sprint2.1 / learning |
| **2.D** | N-rag / N-summary-memory (± vision-rerank ≤N) | **OUT** → AI_RAG / sau |

---

## 2. Toàn bộ out-scope / note từ Sprint1 (master list)

### 2.1 Ứng viên làm trong AI_Chat_Sprint2 (hoặc wave trong sprint)

| ID | Mô tả | Gợi ý wave |
|----|--------|------------|
| N-cite-links | path/url + cite markdown pin/user/tag | 2.A |
| N-skill-listed-pins | search pin đang bán / theo artist | 2.A |
| N-public-vs-private-matrix | BR ranh giới public discovery | 2.A |
| N-search-via-enriched-index | Tìm ảnh qua tag/title/desc (auto-tag đã gắn); không vision all-catalog | 2.A |
| N-forbid-vision-scan-all | Hard rule: không scan vision cả kho mỗi chat turn | 2.A (policy) |
| N-vision-rerank-small-N | Optional rerank ≤N candidates bằng vision | 2.D / sau |
| N-stream | SSE streaming reply | 2.B |
| N-framework | LangChain / LangGraph | 2.C |
| N-router-model | Model classifier tầng 2 | 2.C |
| N-summary-memory | Rolling summary / dual context | 2.D hoặc sau |
| N-msg-delete | API xóa/sửa / clear history | Nhỏ, có thể 2.B |

### 2.2 Tách sprint / backlog xa hơn

| ID | Mô tả | Ghi chú |
|----|--------|---------|
| N-rag | Embed + retrieve FAQ/pin text | `AI_RAG_Sprint` / học RAG |
| N-mutate | Tool ghi (tạo pin, apply, order) + confirm UX | Sau read-only vững |
| N-mongo-ctx | Mongo staging context | Chỉ nếu Postgres history không đủ |
| N-multithread | Nhiều thread / user | Sau 1-thread |
| N-cache-prefix | Gemini context cache | Cost optimize |
| N-ws | WebSocket transport chat | Sau REST+SSE |

### 2.3 Cấm / không làm (giữ nguyên)

| ID | Mô tả |
|----|--------|
| N-autotag-chat | Chatbot gọi auto-tag / retag — **cấm** |
| N-open | Open general ChatGPT — **không** |
| N-guest-chat | Guest chat đầy đủ — **không** (vẫn login gate) |

---

## 3. Đã xong ở Sprint1 (không mang lại trừ regress)

- Schema `ai_conversations` / `ai_messages` / `ai_tool_invocations`  
- Config `AI_CHAT_*`, flag enable  
- 1 Gemini + 4 skills cơ bản + quota + window  
- API POST/GET  
- FAB: optimistic user bubble + typing dots bounce  
- Soft-closed prompt + heuristic offtopic nhẹ  
- Docs LESSON + Plan #1/#2 Sprint1  

---

## 4. Ranh giới data (draft cho BR Sprint2)

| Được (public) | Không |
|---------------|--------|
| Pin của artist X đang **listed** + giá công khai | Order / buyer của user khác |
| Search pin/tag/user profile public + **link path** | Payment method / payout seller |
| Engagement public (likes/saves/views; first liker theo policy Sprint1) | Application của user khác |
| JD **active** + company public | Admin / raw DB / retag |
| Search “nhân vật x” trên pin đã có tag/text khớp | Vision realtime quét toàn bộ pins |

---

## 6. Liên hệ auto-tag (product)

- Cải thiện coverage “nhân vật x” = **chất lượng/prompt auto-tag + backfill**, không = chat gọi model hàng loạt.  
- RAG/embed (N-rag) sau này vẫn **index offline**, query online — cùng nguyên tắc với §1.1.

---

## 5. Trạng thái mở Sprint2

1. ~~Plan #1 quiz~~ — **CHỐT** 2026-11-04 (`1A 2B 3–9A` + rest suggest). Soft-closed **nới art** (Q2 B).  
2. **Tiếp:** Plan #2 — tool schemas, SSE contract, clear API, markdown FE.  
3. Implement theo 2.A+2.B; prove-done AC; **không** code Out BR §6.
