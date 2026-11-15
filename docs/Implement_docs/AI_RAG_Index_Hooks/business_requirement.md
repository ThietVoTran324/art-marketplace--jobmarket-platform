# Business Requirements — AI_RAG_Index_Hooks

**Mức chi tiết:** ~3/10 (business). Schema / task / call-site → Plan #2.  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prereq:** [`../AI_RAG_Index_Automation/`](../AI_RAG_Index_Automation/) (phase B DONE + prove) · FAQ CMS enqueue pattern · Celery `ai_auto_tag`  
**Backlog:** `AI-N-rag-index-auto` phase A · [`../AI_RAG_Sprint1/RAG_FOLLOWUPS.md`](../AI_RAG_Sprint1/RAG_FOLLOWUPS.md)

> **Plan #1 CHỐT** 2026-11-15 — **all suggest** (S1–S8 = A).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | **Phase A:** Sau mutation pin/tag → enqueue Celery **1-item** reindex RAG (không chờ Beat) |
| 2 | Embed **async only**; HTTP create/update không block quota |
| 3 | **Beat B** (missing-only daily) **giữ** làm safety net |
| 4 | Flag opt-in riêng; CLI / Beat B vẫn fallback |
| 5 | Không regress chat / FAQ CMS / Plan A retrieve / Index Automation B |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Hệ thống | Enqueue sau create/update/auto-tag/delete; worker embed hoặc gỡ index |
| User | Tạo/sửa pin/tag bình thường — không thao tác RAG |
| Ops | Bật flag; CLI / Beat B fallback; đọc log |

---

## 3. Quy tắc CHỐT (S1–S8 = A)

| ID | CHỐT |
|----|------|
| C1 | Sprint = **phase A hooks only**; không đổi schedule Beat B (S1 A) |
| C2 | Enqueue **pin** khi: create; title/desc/tags trên pin đổi; **sau auto-tag success** (S2 A) |
| C3 | Enqueue **tag catalog** khi: tag **mới tạo** hoặc **đổi tên** (S3 A) |
| C4 | Flag riêng **`AI_RAG_HOOK_ENABLED`** (default off; opt-in) — không gộp `AI_RAG_AUTO_*` (S4 A) |
| C5 | Queue **`ai_auto_tag`** (cùng worker-ai) (S5 A) |
| C6 | Beat B **luôn** safety net — không tắt khi hook bật (S6 A) |
| C7 | Xóa pin → enqueue **gỡ** doc/chunks RAG async (S7 A) |
| C8 | **Không** Admin UI missing/reindex pins-tags trong sprint (S8 A) |
| C9 | Embed / delete-index **async only**; cấm sync trong HTTP |
| C10 | Không retag trong hook; không thay SQL search; không full daily refresh |

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Hook on + tạo pin → sau worker: có document RAG cho pin đó |
| AC-02 | Đổi title/desc hoặc gắn tag → pin được reindex (nội dung/hash cập nhật) |
| AC-03 | Auto-tag success → pin được enqueue reindex (tags AI vào corpus) |
| AC-04 | Tag mới / đổi tên → embedding catalog cập nhật |
| AC-05 | Flag off → không enqueue; HTTP vẫn nhanh |
| AC-06 | Beat B + CLI `--missing-only` / `--auto-missing` vẫn chạy |
| AC-07 | Chat FAQ + pin retrieve không regress |
| AC-08 | Xóa pin → doc/chunks RAG được gỡ (async) |

---

## 5. Out of scope

| ID | Out |
|----|-----|
| N-admin-reindex-pins-tags | Admin UI (`AI-N-rag-admin-reindex-ui`) |
| N-rag-jd-text / Jina / Vision-OCR | Sau |
| N-beat-change | Đổi crontab / tắt Beat khi hook on |
| N-sync-embed | Embed trong request HTTP |
| N-retag-in-hook | Retag batch / vision scan |
| N-guest-chat | Guest discovery |

---

## 6. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
- [README.md](README.md)  
