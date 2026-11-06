# Business Requirements — AI_Chat_Sprint1 (Platform chatbox MVP)

**Mức chi tiết:** ~3/10 (business). Schema/route/tool payload → Plan #2.  
**Learning SSOT:** [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)

> **Plan #1 CHỐT** 2026-11-03 — quiz chat + S2′ + 1 pipeline AI (không 2 model độc lập MVP).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Chatbox floating trên mọi page (login): hỏi về pin / marketplace / job / account flow |
| 2 | Soft-closed topic: lạc đề rõ → từ chối ngắn, không làm general ChatGPT |
| 3 | Skills (tool) tra cứu: public facts + dữ liệu **của tôi**; backend authz |
| 4 | Một user / một thread / một lịch sử; lưu Postgres |
| 5 | Quota chống burn token; read-only (không mutate hệ thống qua bot) |
| 6 | Tách khỏi auto-tag; chatbot **không** gọi system retag |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Guest | Thấy icon chat; nhấn → yêu cầu đăng nhập; không gửi tin |
| User login | Mở panel góc phải dưới; chat 1 thread; dùng skills trong quyền |
| Hệ thống | Auto-tag / job nền — **không** expose cho chatbot |

---

## 3. Quy tắc (CHỐT Plan #1)

| ID | CHỐT |
|----|------|
| S1 | Soft-closed hội thoại (platform-first) |
| S2′ | Skills trên dữ liệu **phân lớp**: public OK; private chỉ của caller; **không** dump DB; **không** chỉ tin prompt chống inject — authz trong skill/backend |
| S3 | Chỉ login được chat; guest → login gate |
| S4 | History Postgres (SSOT); Mongo staging context = **out / note sau** |
| S5 | 1 user ↔ 1 conversation ↔ 1 lịch sử |
| S6 | Có skills (phân tích / tìm kiếm / tra cứu) — không chat suông-only |
| S7 | Skills “của tôi”: orders **và** applications (read tóm tắt) |
| S8 | Quota: turn/ngày/user + giới hạn độ dài + history window (số → Plan #2) |
| S9 | Lạc đề → từ chối ngắn + kéo về sản phẩm |
| S10 | UI: widget mọi page, góc phải dưới, icon bật/tắt; **không** trộn Messages người–người |
| S11 | Ngôn ngữ theo user / UI locale |
| S12 | Read-only Sprint1; mutate = sau |
| S13 | 1 pipeline AI (1 model chat + skills); tầng rule backend OK; **không** 2 model độc lập MVP |
| S14 | Provider hướng Gemini; config AI chat (chi tiết Plan #2) |
| S15 | Auto-tag / sửa tag = system-only; user & chatbot không gọi |
| S16 | `user_id` từ session; tool không nhận target user tùy ý từ client/model |

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Login gửi tin → nhận reply hoặc reject policy rõ |
| AC-02 | Guest nhấn chat → yêu cầu login; không gọi model |
| AC-03 | Lạc đề rõ → từ chối ngắn; không trả lời dài kiểu general assistant |
| AC-04 | Skill public (vd engagement pin public) không lộ private user khác trái policy |
| AC-05 | Skill “của tôi” chỉ data caller; không đọc user khác |
| AC-06 | History còn sau refresh (1 thread/user) |
| AC-07 | Vượt quota → không gọi model; báo limit rõ |
| AC-08 | Chatbot không trigger auto-tag / retag |
| AC-09 | Messages người–người / feed / auto-tag không regress |
| AC-10 | Widget có trên các page chính (bật/tắt được) |

---

## 5. Out of scope Sprint1 (+ note học/làm sau)

| ID | Out | Note sau |
|----|-----|----------|
| N-stream | Streaming token reply — ưu tiên **SSE** (WS sau) | Sprint UI/UX sau |
| N-rag | RAG / embeddings / vector retrieve | AI_RAG_Sprint / học RAG |
| N-framework | LangChain / LangGraph / LlamaIndex bắt buộc | AI_Chat_Sprint2 học orchestration |
| N-mutate | Tạo pin / apply / order qua bot | Sau + confirm UX |
| N-mongo-ctx | Mongo làm staging context AI | Chỉ nếu Postgres history không đủ |
| N-multithread | Nhiều thread/user | Sau khi 1-thread ổn |
| N-router-model | Model classifier/router tầng 2 | **Sprint chat đầy đủ tiếp theo** (sau 1-model MVP) |
| N-summary-memory | Rolling summary / dual chat context | Khi history window không đủ |
| N-cache-prefix | Gemini context cache | Tối ưu cost sau |
| N-guest-chat | Guest chat đầy đủ | Không |
| N-open | Open general assistant | Không |
| N-autotag-chat | Chat gọi retag | Cấm; system job only |
| N-cite-links | Cite pin/user/tag kèm path/url trong reply | Sprint2 — [`../AI_Chat_Sprint2/PRELIMINARY_PLAN.md`](../AI_Chat_Sprint2/PRELIMINARY_PLAN.md) |
| N-skill-listed-pins | Skill pin đang rao bán / theo artist (public) | Sprint2 |
| N-public-vs-private-matrix | Làm rõ public marketplace discovery ≠ private | Sprint2 |
| N-search-via-enriched-index | Tìm ảnh qua tag/index (auto-tag offline); cấm vision all-catalog | Sprint2 §1.1 |

---

## 6. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
- Learning: [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)
