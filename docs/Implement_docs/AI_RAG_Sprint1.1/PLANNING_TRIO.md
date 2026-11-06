# Bộ 3 planning — AI_RAG_Sprint1.1 (Plan A)

> pin-text + parent-child + hybrid RRF + **intent→tags bridge**  
> Prereq: AI_RAG_Sprint1 · AI_Chat_Sprint2  
> Eval Intent-tags: BR §4

| File | Vai trò | Thời điểm |
|------|---------|-----------|
| [business_requirement.md](business_requirement.md) | SSOT nghiệp vụ | **Plan #1 CHỐT** 2026-11-06 |
| [base requirement.md](base%20requirement.md) | Input ngắn | Đã dùng |
| [plan_mode_decisions.md](plan_mode_decisions.md) | Tech | **Plan #2 CHỐT** 2026-11-06 |
| [devplan_checklist.md](devplan_checklist.md) | Checklist | Ready — chờ implement |
| [README.md](README.md) | Gate | Cập nhật |

## Quyết định Plan #1

| Q | Chọn |
|---|------|
| 1 | **A** full Plan A |
| 2 | **C′** title+desc+tags; **không** index incorrect_tags |
| 3 | **A** parent=pin / child=đoạn |
| 4 | **A** + Intent→tags (English; skill mới; không retag) |
| 5–7 | **A** hybrid RRF · SQL giữ · offline reindex |
| 8–11 | suggest |

## Gate

- [x] Plan #1 CHỐT  
- [x] Plan #2 CHỐT (`all suggest`)  
- [ ] Implement  

| Plan | Status |
|------|--------|
| Plan #1 | **CHỐT** 2026-11-06 |
| Plan #2 | **CHỐT** 2026-11-06 |
| Implement | **DONE** (code) 2026-11-06 — migrate + reindex tags/pins + prove |

**Intent rule:** mọi ngôn ngữ user → `predicted_tags` English kebab-case only.
