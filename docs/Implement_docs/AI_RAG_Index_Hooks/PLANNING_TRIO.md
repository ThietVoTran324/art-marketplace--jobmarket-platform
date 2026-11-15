# Bộ 3 planning — AI_RAG_Index_Hooks

> Initiative: **Auto index pin/tag RAG — phase A hooks**  
> Prereq: Index Automation phase B DONE · FAQ CMS · Celery AI queue  
> Map: Planing §K · `AI-N-rag-index-auto` phase A

| File | Vai trò | Thời điểm |
|------|---------|-----------|
| [business_requirement.md](business_requirement.md) | SSOT nghiệp vụ | **Plan #1 CHỐT** 2026-11-15 |
| [base requirement.md](base%20requirement.md) | Input ngắn | Đã dùng |
| [plan_mode_decisions.md](plan_mode_decisions.md) | Tech | **Plan #2 CHỐT** 2026-11-15 |
| [devplan_checklist.md](devplan_checklist.md) | Checklist | Implement + prove DONE |
| [README.md](README.md) | Gate | Cập nhật |

## Quyết định Plan #1 (`all suggest`)

| S | Chọn |
|---|------|
| S1 | **A** phase A hooks only |
| S2 | **A** pin: create + text/tag đổi + sau auto-tag success |
| S3 | **A** tag: mới + đổi tên |
| S4 | **A** `AI_RAG_HOOK_ENABLED` riêng |
| S5 | **A** queue `ai_auto_tag` |
| S6 | **A** Beat B giữ safety net |
| S7 | **A** xóa pin → gỡ RAG async |
| S8 | **A** không Admin UI |

## Quyết định Plan #2 (`all suggest`)

| T | Chọn |
|---|------|
| T1–T10 | **A** (xem plan_mode_decisions.md) |

## Gate

- [x] Plan #1 CHỐT (`all suggest`)  
- [x] Plan #2 CHỐT (`all suggest`)  
- [x] Implement  
- [x] Prove-done 2026-11-15  

| Plan | Status |
|------|--------|
| Plan #1 | **CHỐT** 2026-11-15 |
| Plan #2 | **CHỐT** 2026-11-15 |
| Implement | **DONE** 2026-11-15 |
| Prove | **DONE** 2026-11-15 |
