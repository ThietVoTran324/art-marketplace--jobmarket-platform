# Business Requirements — AI_Chat_Sprint2 (Discovery + cite + SSE)

**Mức chi tiết:** ~3/10 (business). Schema/route/SSE contract → Plan #2.  
**Learning SSOT:** [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prereq:** [`../AI_Chat_Sprint1/`](../AI_Chat_Sprint1/) MVP (1 model, window memory, skills, FAB)

> **Plan #1 CHỐT** 2026-11-04 — quiz chat: `1A 2B 3A 4A 5A 6A 7A 8A 9A` + còn lại **all suggest**.

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | **Discovery marketplace công khai:** “artist X đang bán gì?” → list pin `listed` + giá public + link, không chỉ “tự vào marketplace” |
| 2 | **Cite có link:** pin / user / tag trong reply có path clickable (markdown FE) |
| 3 | **Search hình qua index:** title / description / **tag** (auto-tag offline); không thấy → nói rõ; **cấm** vision-scan cả catalog |
| 4 | **Matrix public vs private** viết rõ (tránh soft-closed = cấm mọi Q&A marketplace) |
| 5 | **SSE** stream token reply + FE markdown links |
| 6 | **Clear** 1 conversation/user (không multi-thread) |
| 7 | Giữ: soft-closed (nới nhẹ art), login-only, 1 thread, Postgres, read-only, quota, **cấm** chatbot retag |

**Sóng ship CHỐT:** **2.A** (discovery/cite/listed/index) + **2.B** (SSE + markdown FE). **Không** 2.C/2.D trong sprint này.

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Guest | Icon chat → login gate; **không** chat (giữ Sprint1) |
| User login | Chat 1 thread; discovery public + “của tôi”; clear history; nhận stream (SSE) |
| Hệ thống | Auto-tag / backfill offline làm giàu index — **không** expose cho chatbot |

---

## 3. Quy tắc (CHỐT Plan #1)

| ID | CHỐT |
|----|------|
| S2-01 | Scope = wave **2.A + 2.B** (cite, listed-pins, matrix, search-index, SSE, markdown FE, clear) |
| S2-02 | Soft-closed **nới nhẹ**: được tư vấn nghệ thuật chung dài hơn Sprint1; vẫn **không** open general ChatGPT / lạc đề hoàn toàn ngoài art+platform |
| S2-03 | **Matrix public vs private** (xem §4) — discovery listed = public |
| S2-04 | Cite: skill trả `path` relative; prompt bắt markdown `[title](path)`; FE render clickable |
| S2-05 | Skill **listed-pins** (hoặc flag tương đương): filter `listed` + optional artist/query; giá public + path |
| S2-06 | Search ảnh = query **title / description / tag**; thiếu → “chưa có trong index”; **cấm** vision-scan all-catalog |
| S2-07 | Auto-tag/backfill **offline** phục vụ index; chat **không** enqueue retag / vision on-demand retag |
| S2-08 | Streaming reply = **SSE** (WebSocket = out) |
| S2-09 | FE: markdown link + bubble bot hỗ trợ click `path` (không bắt buộc rich pin-card Sprint2) |
| S2-10 | LangChain / LangGraph = **out** Sprint2 (note học Sprint2.1 / learning path) |
| S2-11 | Giữ **1 model** + rule/prompt; router / 2-model = **out** |
| S2-12 | RAG / embeddings = **out** → `AI_RAG_Sprint` |
| S2-13 | Rolling summary memory = **out**; giữ history window |
| S2-14 | Có **clear conversation** (1 thread); không xóa từng message; không multi-thread |
| S2-15 | Vẫn **read-only** — không mutate pin/apply/order qua bot |
| S2-16 | Cite: absolute `url` (`FRONTEND_DOMAIN`) **bắt buộc** (Plan #2 T2 C); `path` relative kèm theo; pin kèm **thumb** (collection = ảnh đầu) |
| S2-17 | Guest → login; không guest discovery chat |
| S2-18 | Giữ skills Sprint1 + listed-pins + cite path trên mọi skill trả pin/user/tag; search pins dùng tag index |
| S2-19 | Authz vẫn skill/backend; không dump DB; không tin prompt thay gate (Sprint1 S2′/S16) |
| S2-20 | Provider / quota / session `user_id` giữ hướng Sprint1 (số liệu Plan #2) |

---

## 4. Matrix public vs private (CHỐT)

| Được (public discovery) | Không (private / hard-closed) |
|-------------------------|-------------------------------|
| Pin của artist X đang **listed** + giá công khai + path | Order / buyer của user khác |
| Search pin / tag / user profile **public** + path | Payment method / payout seller |
| Engagement public (likes/saves/views; first-liker theo policy Sprint1) | Application của user khác |
| JD **active** + company public + path | Admin / raw DB |
| Search “nhân vật X” trên index tag/title/desc đã có | Vision realtime quét toàn bộ pins |
| Orders / applications **của tôi** (tóm tắt, như Sprint1) | Chatbot gọi auto-tag / retag |

Soft-closed **không** có nghĩa “cấm mọi câu marketplace”. Cấm = private leak + open ChatGPT + mutate + retag.

---

## 5. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | “Artist X đang bán?” → list listed (hoặc “không có”); không chỉ “vào marketplace tự xem” |
| AC-02 | Kết quả pin/user/tag có link bấm đúng route (markdown / path) |
| AC-03 | Search theo title/desc/tag index; không vision-scan catalog |
| AC-04 | Không lộ private (orders/apps người khác, payout…) |
| AC-05 | Soft-closed nới art OK; lạc đề hoàn toàn / open assistant vẫn từ chối; quota / no-retag giữ |
| AC-06 | SSE stream hoạt động hoặc degrade rõ (fallback non-stream) |
| AC-07 | Clear history (1 conversation) được; refresh không còn message cũ |
| AC-08 | Sprint1 chat / Messages / feed / auto-tag không regress |
| AC-09 | Guest vẫn login gate |
| AC-10 | Absolute URL không bắt buộc nếu relative path + FE resolve đúng |

---

## 6. Out of scope Sprint2 — **note rõ (bắt buộc giữ)**

Mọi item dưới đây **không implement** trong Sprint2 trừ khi user mở lại Plan #1. Ghi learning / sprint đích để khỏi quên.

### 6.1 Defer — sprint / wave sau (học hoặc ship sau)

| ID | Out Sprint2 | Ghi note / đích |
|----|-------------|-----------------|
| **N-framework** | LangChain / LangGraph / LlamaIndex bắt buộc refactor orchestration | **Sprint2.1** / learning path khối orchestration — sau khi 2.A+2.B ổn |
| **N-router-model** | Model classifier / router tầng 2 (2 model độc lập) | Sprint chat sau; giữ 1 model |
| **N-rag** | Embeddings / vector retrieve / cite từ chunk | **`AI_RAG_Sprint`** |
| **N-summary-memory** | Rolling summary / dual chat context | Khi history window không đủ |
| **N-vision-rerank-small-N** | SQL top-N (≤20) rồi vision rerank | Sau; **không** mở thành scan-all |
| **N-mutate** | Tạo pin / apply / order qua bot (+ confirm UX) | Sau read-only vững |
| **N-mongo-ctx** | Mongo staging context AI | Chỉ nếu Postgres history không đủ |
| **N-multithread** | Nhiều thread / rename thread | Sau 1-thread + clear ổn |
| **N-msg-edit-delete** | Xóa/sửa **từng** message | Chỉ có **clear all** trong Sprint2 |
| **N-cache-prefix** | Gemini context cache | Cost optimize sau |
| **N-ws** | WebSocket transport chat | Sau REST + SSE |
| **N-rich-pin-card** | Chip/card pin rich UI | Sau markdown links cơ bản |
| **N-absolute-url-required** | Bắt buộc absolute URL mọi cite | Relative path CHỐT; absolute optional Plan #2 |
| **N-guest-discovery** | Guest hỏi public discovery không login | Không — giữ login gate |

### 6.2 Cấm / không làm (giữ nguyên, không “sau”)

| ID | Mô tả |
|----|--------|
| **N-autotag-chat** | Chatbot gọi / enqueue auto-tag / retag — **cấm** |
| **N-vision-scan-all** | Vision trên toàn catalog mỗi câu hỏi — **cấm** (cost + latency) |
| **N-open** | Open general ChatGPT (ngoài art+platform) — **không** |
| **N-guest-chat** | Guest chat đầy đủ như user — **không** |
| **N-dump-db** | Skill dump raw DB / bỏ authz — **không** |

### 6.3 Đã kéo **vào** Sprint2 (không còn “note sau” như Sprint1)

| ID | Trạng thái |
|----|------------|
| N-cite-links | **IN** 2.A |
| N-skill-listed-pins | **IN** 2.A |
| N-public-vs-private-matrix | **IN** (BR §4) |
| N-search-via-enriched-index | **IN** 2.A |
| N-forbid-vision-scan-all | **IN** (policy cứng) |
| N-stream (SSE) | **IN** 2.B |
| N-msg-clear (clear conversation) | **IN** (Q14 B) |

---

## 7. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
- Backlog sóng cũ (tham chiếu): [PRELIMINARY_PLAN.md](PRELIMINARY_PLAN.md)  
- Learning: [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)
