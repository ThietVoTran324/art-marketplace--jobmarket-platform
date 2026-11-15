# Business Requirements — AI_RAG_FAQ_CMS

**Mức chi tiết:** ~3/10 (business). Schema / route payload → Plan #2.  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prereq:** [`../AI_RAG_Sprint1/`](../AI_RAG_Sprint1/) (FAQ md + retrieve) · [`../AI_RAG_Sprint1.1/`](../AI_RAG_Sprint1.1/) Plan A · Admin shell `/admin`  
**Backlog:** `AI-N-rag-faq-cms` (Sprint1 Plan #2 T1 → B)

> **Plan #1 CHỐT** 2026-11-13 — **all suggest** (S1–S8 = A).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Admin **tạo / sửa / ẩn** FAQ sản phẩm trên UI Admin |
| 2 | FAQ **Published** là nguồn RAG chat (cite `faq:…`); Draft không vào index |
| 3 | **DB = SSOT** cho FAQ dùng bởi RAG; markdown git chỉ **seed/import một lần** |
| 4 | Publish / unpublish → **reindex bài đó**; có nút **Reindex all FAQ** tối thiểu |
| 5 | Giữ login-only chat, SQL tools, Plan A pin/intent; không retag / vision-scan-all |
| 6 | CLI reindex FAQ vẫn là fallback ops |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Admin (`admin`) | CRUD FAQ; publish/unpublish/archive; reindex FAQ (bài / all) |
| User login | Chat how-to dựa FAQ đã publish + đã index |
| Guest | Không chat CMS; không CMS |
| Hệ thống | Chunk → embed → vector (pipeline hiện có); job/queue reindex |

---

## 3. Quy tắc CHỐT (S1–S8 = A)

| ID | CHỐT |
|----|------|
| C1 | **DB = SSOT** FAQ cho RAG; md = seed/import một lần (S1 A) |
| C2 | Chỉ role **admin** sửa CMS (S2 A) |
| C3 | **Draft / Published**; chỉ Published được index (S3 A) |
| C4 | Publish/unpublish → reindex **bài đó**; + nút reindex **all FAQ** (S4 A) |
| C5 | Sprint gồm CMS FAQ + reindex FAQ; **không** UI reindex pins/tags (S5 A) |
| C6 | **Một body** ngôn ngữ do admin viết; không bắt buộc VI+EN (S6 A) |
| C7 | **Unpublish / archive** mặc định; hard delete optional (S7 A) |
| C8 | **Không** trang FAQ `/help` public; không dump FAQ cho guest (S8 A) |
| C9 | Cite bắt buộc khi retrieve FAQ; thiếu context → không bịa |
| C10 | Không index private orders/apps/payout; không chat mutate FAQ |
| C11 | Chat Sprint2 + Plan A không regress |

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Admin tạo/sửa draft; chưa publish → chat không lấy bài đó |
| AC-02 | Publish → sau reindex → hỏi đúng chủ đề → trả lời + cite FAQ |
| AC-03 | Unpublish → reindex → chat không còn dựa bài đó |
| AC-04 | Seed/import từ md corpus hiện có một lần → FAQ cũ vẫn trả lời được |
| AC-05 | User thường / guest không vào CMS |
| AC-06 | Chat + Plan A pin/intent không regress |
| AC-07 | Không retag / không index private user data qua CMS |
| AC-08 | CLI reindex FAQ vẫn chạy được |

---

## 5. Out of scope

| ID | Out |
|----|-----|
| N-help-public | Trang `/help` public |
| N-admin-reindex-pins-tags | UI reindex pins/tags (`AI-N-rag-admin-reindex-ui` phần còn lại) |
| N-rag-jd-text | Embed JD |
| N-rag-jina-live | Jina bắt buộc |
| N-rag-doc-vision-ocr | Vision-OCR |
| N-faq-i18n | Bản bắt buộc đa ngôn ngữ |
| N-faq-versioning | Version history đầy đủ |
| Feed Search leftover | `v-auto-animate` / WebP / SEARCH Type2 |

---

## 6. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
