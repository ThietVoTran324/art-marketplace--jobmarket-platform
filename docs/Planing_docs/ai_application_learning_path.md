# AI application — learning path (vừa làm vừa hiểu)

**Mục tiêu:** Học đúng những gì JD **Junior Backend AI / AI Application Engineer** hay yêu cầu, gắn vào feature thật của repo.  
**Đã làm quen:** Gemini vision auto-tag pins (API call, prompt, structured JSON, Celery, rate limit).  
**Bắt đầu học cơ bản:** AI Chatbox (orchestration, memory, tools, guardrails → sau đó RAG).

> Không cần học song song cả LangChain **và** LlamaIndex. Concept trước → **một** framework orchestration → RAG sau.

---

## 0. Quy trình phát triển feature AI trong PJ (chuẩn repo)

Thứ tự **bắt buộc** (khớp Plan mode sprint):

| Bước | Việc | Không làm sớm |
|------|------|----------------|
| **1. Plan #1** | Business: scope, actors, soft/hard boundary, AC, out of scope | Không chốt tên bảng / payload API |
| **2. Plan #2** | Tech: schema, routes, tool contracts, model/provider, quota | Không code trước khi `all suggest` |
| **3. Implement** | Migration → API → worker/UI → smoke | Không nới scope Type2 |
| **4. Prove-done** | Checklist + eval sơ bộ (cost, từ chối off-topic, authz tool) | — |

**Thiết kế CSDL** thuộc **Plan #2 / đầu implement**, **không** phải bước đầu tiên. Đầu tiên = **chốt plan sprint**.

Initiative: [`../Implement_docs/AI_Chat_Sprint1/`](../Implement_docs/AI_Chat_Sprint1/).

---

## 1. Map JD junior → khối học → feature

| # | Khối (JD hay ghi) | Concept cần nắm | Gắn feature |
|---|-------------------|-----------------|-------------|
| 1 | LLM I/O | Prompt, token, RPM/RPD, structured output, latency | Auto-tag (xong) + mỗi turn chat |
| 2 | Guardrails | Soft-closed topic, hard-closed data, PII | Chat policy + tool authz |
| 3 | Memory | History store, window N turn, optional summary | Postgres conversations |
| 4 | Tool / function calling | Model chọn tool → backend chạy → trả kết quả | Search pin / JD / order *của user* |
| 5 | Orchestration framework | Agents, chains, graph (LangChain **hoặc** LangGraph) | Refactor chat sau MVP thuần |
| 6 | RAG | Chunk, embed, vector search, cite sources | Sprint sau: FAQ + mô tả pin/JD |
| 7 | Eval / LLMOps lite | Groundedness, log, cost, fail-soft | Log turn + quota + vài case test |
| 8 | Backend ship | FastAPI, SQL, Docker, Git, secrets | Đã có — nhấn trên CV |

**Để sau (không chặn junior app):** fine-tune/LoRA, multi-agent phức tạp, MCP production, train model.

---

## 2. Lộ trình sprint học (đề xuất)

| Phase | Ship | Học chính |
|-------|------|-----------|
| **Done** | Auto-tag + backfill | LLM API, vision, prompt, queue, quota |
| **AI_Chat_Sprint1** | Chat MVP: soft-closed + Postgres history + 2–3 tools + quota | Memory, tools, guardrails, cost |
| **AI_Chat_Sprint2** | Cite + listed-pins + search index/tag; SSE + markdown; clear; soft-closed nới art — **không** vision-scan-all, **không** LangChain/router/RAG trong sprint | Plan #1 CHỐT [`../Implement_docs/AI_Chat_Sprint2/business_requirement.md`](../Implement_docs/AI_Chat_Sprint2/business_requirement.md) |
| **AI_Chat_Sprint2.1** (sau) | LangChain/LangGraph ± router model (N-framework, N-router-model) | Học orchestration sau khi 2.A+2.B ổn |
| **AI_RAG_Sprint1** | FAQ → chunk → embed (API) → PG vector → retrieve + cite + chat tool; SQL tools giữ; **roadmap** FAQ+pin (C) | Plan #1 CHỐT [`../Implement_docs/AI_RAG_Sprint1/business_requirement.md`](../Implement_docs/AI_RAG_Sprint1/business_requirement.md) |

---

## 3. Quyết định product (Plan #1 CHỐT 2026-11-03)

SSOT: [`../Implement_docs/AI_Chat_Sprint1/business_requirement.md`](../Implement_docs/AI_Chat_Sprint1/business_requirement.md)

| ID | Hướng | Ghi chú |
|----|--------|---------|
| S-topic | Soft-closed hội thoại | Từ chối lạc đề ngắn |
| S2′ | Skills + dữ liệu phân lớp public / private-của-tôi | Authz backend; không dump DB; không chỉ tin prompt |
| S-store | Postgres 1 thread/user | Mongo staging = N-mongo-ctx sau |
| S-layer | 1 pipeline AI MVP | N-router-model sau |
| S-turn | 1 user message ≈ 1 API call | Window + quota + reject sớm |
| Out notes (S1) | Nhiều N-* đã kéo vào Sprint2 (cite/listed/SSE…) | Sprint1 BR §5 |
| Sprint2 Out | N-framework · N-router-model · N-rag · N-summary-memory · N-vision-rerank · N-mutate · N-ws · … + cấm N-autotag-chat / N-vision-scan-all | Sprint2 BR §6 |

**Plan #2 CHỐT 2026-11-03:** 1 model + window history + skills; bảng tool_invocations; meta JSONB bắt buộc. Xem [`../Implement_docs/AI_Chat_Sprint1/plan_mode_decisions.md`](../Implement_docs/AI_Chat_Sprint1/plan_mode_decisions.md).

---

## 4. Gợi ý học khi implement Sprint1

Mỗi PR/wave tự hỏi:

1. Prompt system đang **chặn gì** / **cho phép gì**?
2. History gửi lên model **bao nhiêu turn** — cắt thế nào?
3. Tool này **authz** ra sao (chỉ data của caller)?
4. Off-topic có **tốn đủ 1 full answer** không, hay reject sớm?
5. Fail Gemini/429 xử lý thế nào với UX?

Framework LangChain: chỉ kéo vào khi MVP thuần đã chạy — tránh học framework trước concept.
