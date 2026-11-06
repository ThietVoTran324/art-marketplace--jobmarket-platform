# Business Requirements — AI_RAG_Sprint1 (RAG pipeline MVP)

**Mức chi tiết:** ~3/10 (business). Schema/embed provider/payload → Plan #2.  
**Learning SSOT:** [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prereq:** [`../AI_Chat_Sprint1/`](../AI_Chat_Sprint1/) + [`../AI_Chat_Sprint2/`](../AI_Chat_Sprint2/) (tools, cite, SSE, soft-closed, login-only)

> **Plan #1 CHỐT** 2026-11-05 — `1A 2A(→C) 3–7A` + còn lại **all suggest**.

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Luồng RAG chuẩn **một sprint**: chọn corpus → **chunk** → **embed** → **vector store** → **retrieve** → **cite** → gắn **chat** |
| 2 | User login hỏi kiến thức **FAQ / hướng dẫn sản phẩm** → trả lời dựa chunk + cite nguồn; không bịa khi thiếu context |
| 3 | Giữ skills SQL Sprint1–2 (listed, orders, search tag…); RAG **bổ sung**, không thay |
| 4 | Index **offline / job reindex**; chat không embed cả kho realtime mỗi câu |
| 5 | Embed qua **API** (không self-host model nặng trên VPS ~4 GiB) |
| 6 | Lộ trình corpus: **MVP = FAQ (A)**; **hướng tới FAQ + pin text (C)** ở wave sau cùng initiative / sprint kế |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Guest | Login gate — không chat / không RAG (giữ chat) |
| User login | Chat như Sprint2; câu “làm sao / quy trình / FAQ” có thể dùng retrieve |
| Hệ thống | Job/script chunk+embed+reindex corpus public; **không** chatbot retag / vision-scan-all |

---

## 3. Quy tắc (CHỐT Plan #1)

| ID | CHỐT |
|----|------|
| R1 | Scope = **full pipeline MVP** gắn chat (Q1 A) |
| R2 | Corpus **sprint này = FAQ / hướng dẫn sản phẩm** (Q2 A). **Roadmap:** tiến **FAQ + pin text (C)** — note wave `1.1` / sprint kế; **không** bắt buộc pin embed trong AC đóng Sprint1 nếu chưa kịp |
| R2b | FAQ nguồn MVP = file seed git; **bản cuối hướng CMS/DB editable** (`N-rag-faq-cms`) — Plan #2 T1 A→B |
| R3 | Gắn chat bằng **tool/skill retrieve**; model gọi khi hỏi kiến thức; fact marketplace / “của tôi” vẫn SQL skills |
| R4 | Cite nguồn chunk **bắt buộc** khi dùng RAG; thiếu context → nói không chắc / không bịa |
| R5 | Index offline + **reindex** khi corpus đổi |
| R6 | Vector store hướng **Postgres + vector** (chi tiết Plan #2) |
| R7 | Embed **API 3rd party** (ứng viên Jina / Gemini embed — chốt Plan #2); **cấm** self-host nặng trên soft-live hiện tại |
| R8 | Không thay `search_pins` / listed bằng vector trong sprint này |
| R9 | Rolling summary memory = **out** |
| R10 | LangChain / LlamaIndex **không bắt buộc** (tự build retrieve+prompt OK) |
| R11 | Login-only |
| R12 | Chỉ index corpus **public** đã chọn; không orders/apps/payout người khác; soft-closed art+platform giữ; không open ChatGPT |
| R13 | Eval tối thiểu: FAQ+cite; ngoài corpus không bịa; SQL tools vẫn đúng; cost/quota không nổ |
| R14 | Chat Sprint2 không regress (SSE, cite pin/job, clear, listed…) |
| R15 | Cấm: chat retag, vision-scan-all, dump DB |

---

## 4. Lộ trình corpus (A → C)

| Wave | Corpus | Trạng thái |
|------|--------|------------|
| **1.0 (sprint này)** | FAQ / help sản phẩm (list pin, mua bán, apply, chat rules…) | **IN — CHỐT** |
| **1.1 (hướng tới)** | FAQ + **pin text** (title/description/tags) semantic | **Roadmap** — Plan #1 ghi nhận tiến về Q2 C; mở Plan riêng hoặc mở rộng khi 1.0 đóng |
| Sau | + JD text (Q2 D) | Out trừ khi mở lại |

---

## 5. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Hỏi trong FAQ corpus → trả lời + **cite** nguồn |
| AC-02 | Ngoài corpus / retrieve yếu → không bịa policy/fact |
| AC-03 | “Artist đang bán?” / orders của tôi → vẫn skill SQL; không chỉ RAG |
| AC-04 | Pipeline chunk → embed → lưu vector → retrieve (+ reindex) chạy được |
| AC-05 | Embed API; không self-host nặng; không index private orders/apps |
| AC-06 | Chat Sprint2 không regress |
| AC-07 | Login-only |
| AC-08 | (Roadmap note) Pin-text corpus **không** bắt buộc để đóng 1.0; có checklist/note wave 1.1 |

---

## 6. Out of scope — note rõ

### 6.1 Out sprint này (defer)

| ID | Out | Đích |
|----|-----|------|
| **N-rag-pin-text** | Embed pin title/desc/tags | Wave **1.1** (tiến về Q2 C) |
| **N-rag-jd-text** | Embed JD | Sau |
| **N-summary-memory** | Rolling summary | Sau |
| **N-framework** | LangChain / LlamaIndex bắt buộc | Chat 2.1 / optional sau |
| **N-router-model** | 2-model router | Sau |
| **N-multimodal-embed** | Image / vision embed | Sau (khác FEED-P4b) |
| **N-replace-sql-search** | Thay search_pins/listed bằng vector | Không |
| **N-self-host-embed** | Sentence-transformers trên VPS 4 GiB | **Reject** soft-live hiện tại |
| **N-feed-p4-inject** | Inject embed vào home feed | Stream feed riêng (FEED-P4) |
| **N-mutate** / **N-multithread** / **N-ws** | Như chat Out | Giữ |

### 6.2 Cấm

| ID | Mô tả |
|----|--------|
| N-autotag-chat | Chat gọi retag |
| N-vision-scan-all | Vision cả catalog mỗi câu |
| N-open | Open general ChatGPT |
| N-guest-chat | Guest full chat |
| N-dump-db / N-index-private | Index private user data vào vector SSOT |

---

## 7. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
- Learning: [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)
