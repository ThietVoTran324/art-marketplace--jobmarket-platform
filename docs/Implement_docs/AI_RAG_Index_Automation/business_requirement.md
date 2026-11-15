# Business Requirements — AI_RAG_Index_Automation

**Mức chi tiết:** ~3/10 (business). Schema / schedule payload → Plan #2.  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prereq:** [`../AI_RAG_Sprint1.1/`](../AI_RAG_Sprint1.1/) · [`../AI_RAG_FAQ_CMS/`](../AI_RAG_FAQ_CMS/) · Celery AI queue  
**Backlog:** `AI-N-rag-index-auto` · [`../AI_RAG_Sprint1/RAG_FOLLOWUPS.md`](../AI_RAG_Sprint1/RAG_FOLLOWUPS.md)

> **Plan #1 CHỐT** 2026-11-14 — **all suggest** (S1–S8 = A).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | **Phase B:** Job định kỳ tự index **pin/tag RAG còn thiếu** (không phụ thuộc ops chạy tay mỗi ngày) |
| 2 | Tôn trọng **quota / VPS**: limit + pause; dừng sạch khi rate-limit |
| 3 | CLI `reindex_rag --pins/--tags` vẫn là **fallback** |
| 4 | **Phase A (roadmap):** sau B ổn — enqueue 1 pin/tag khi create/update; **B giữ safety net** |
| 5 | Không regress chat / FAQ CMS / Plan A retrieve |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Hệ thống | Beat/scheduled job; (sau) Celery enqueue 1-item |
| Ops/admin | CLI fallback; đọc log/stats job |
| User | Không thao tác trực tiếp |

---

## 3. Quy tắc CHỐT (S1–S8 = A)

| ID | CHỐT |
|----|------|
| C1 | Sprint này = **phase B only**; phase A = note/roadmap trong BR (S1 A) |
| C2 | Tần suất mặc định **1 lần/ngày** cửa sổ cố định (S2 A) |
| C3 | Pins: chỉ **missing** (chưa có doc RAG) (S3 A) |
| C4 | Tags: chỉ **missing / hash lệch** (S4 A) |
| C5 | Limit mặc định product: pins **≤50**/run, tags **≤200**/run — config được (S5 A) |
| C6 | Không khuyến nghị chồng cửa sổ với retag nặng; 1 AI-heavy batch/lúc (S6 A) |
| C7 | Phase A sau B: hook enqueue 1 pin / 1 tag; B vẫn chạy (S7 A) |
| C8 | **Không** Admin UI backlog counts trong sprint (S8 A) |
| C9 | Embed **async** only; cấm sync trong HTTP tạo pin/tag |
| C10 | Không thay SQL search; không retag trong job này |

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Schedule/Beat chạy được trên compose local (và documented cho prod) |
| AC-02 | Sau run: `pin_docs` / tag embeddings tăng với bản ghi missing; đã có thì skip |
| AC-03 | Limit + pause config được tôn trọng; 429 → dừng sạch, worker không chết |
| AC-04 | CLI `--pins` / `--tags` vẫn dùng được |
| AC-05 | BR/README ghi phase A roadmap; **không** bắt buộc implement hook để đóng sprint |
| AC-06 | Chat + FAQ retrieve + Plan A không regress |

---

## 5. Out of scope

| ID | Out |
|----|-----|
| Phase A hook implement | Sprint sau (khi B ổn) |
| Admin UI “RAG missing counts” | Cùng/sau admin-reindex UI |
| N-rag-jd-text / Jina / Vision-OCR | Sau |
| Daily retag auto | Tool/ops riêng (không gộp sprint này) |
| Full reindex mọi pin mỗi ngày | Reject mặc định (S3) |

---

## 6. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
