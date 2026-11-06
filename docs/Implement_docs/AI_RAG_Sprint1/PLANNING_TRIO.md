# Bộ 3 planning — AI_RAG_Sprint1

> Initiative: **AI_RAG_Sprint1 — chunk → embed → vector → retrieve → cite → chat (FAQ)**  
> Roadmap corpus: **A (FAQ) → C (FAQ + pin text)**  
> Prereq: AI_Chat_Sprint1 + Sprint2  
> Learning: [`../../Planing_docs/ai_application_learning_path.md`](../../Planing_docs/ai_application_learning_path.md)  
> Rule: [`../lessonlearn.md`](../lessonlearn.md)

| File | Vai trò | Thời điểm |
|------|---------|-----------|
| [business_requirement.md](business_requirement.md) | SSOT nghiệp vụ | **Plan #1 CHỐT** 2026-11-05 |
| [base requirement.md](base%20requirement.md) | Input Plan #1 | Đã dùng |
| [plan_mode_decisions.md](plan_mode_decisions.md) | SSOT kỹ thuật | **Plan #2 CHỐT** 2026-11-05 |
| [devplan_checklist.md](devplan_checklist.md) | Thực thi | Ready — chờ lệnh implement |
| [README.md](README.md) | Gate + status | Cập nhật |

## Quyết định Plan #1 (tóm tắt)

| Q | Chọn |
|---|------|
| 1 | **A** full pipeline + gắn chat |
| 2 | **A** FAQ now → **hướng C** FAQ+pin (wave 1.1) |
| 3–7 | **A** tool retrieve · cite · offline index · PG vector · API embed |
| 8–14 | **all suggest** (giữ SQL search · summary out · no framework bắt buộc · login · public only · eval tối thiểu · Out package) |

## Gate vào

- [x] Plan #1 CHỐT  
- [x] Plan #2 tech CHỐT (`T1A→B note`, `T3C` Gemini default + config)  
- [ ] Chat Sprint2 usable local (khuyến nghị)

## Gate đóng (sau implement)

- [ ] AC BR §5  
- [ ] Out/nợ plan_mode §7 không sót  
- [ ] Không regress chat Sprint2  

## Trạng thái Plan

| Plan | Trạng thái |
|------|------------|
| Plan #1 | **CHỐT** 2026-11-05 |
| Plan #2 | **CHỐT** 2026-11-05 |
| Implement | **DONE** (code) 2026-11-05 — migrate + reindex + prove-done |

**Nợ bản cuối:** FAQ CMS (`N-rag-faq-cms`); pin text wave 1.1 (`N-rag-pin-text`).
