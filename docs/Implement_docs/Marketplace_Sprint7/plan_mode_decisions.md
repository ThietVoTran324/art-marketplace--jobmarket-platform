# Plan #2 decisions — Marketplace_Sprint7 (Phase 2.7)

> **CHỐT** 2026-09-28 — `all suggest` từ Plan #2 quiz. Implement **CLOSED** cùng ngày.  
> Prerequisite Alembic head: `f8a9b0c1d2e3` → shipped `a9b0c1d2e3f4`

| ID | CHỐT |
|----|------|
| T1 | Watermark: Pillow text band + logo trong `apply_watermark` |
| T2 | Regenerate preview cho pin có `original_image` (Celery task/script); list fail nếu chưa ready |
| T3 | `assert_pin_media_ready` trên create/relist listing |
| T4 | Strip `original_image` khỏi public `PinOut`; thêm `has_original: bool` |
| T5 | Table `pin_original_access_logs` |
| T6 | Log **mint** signed URL và **file** hit |
| T7 | Migration `a9b0c1d2e3f4` ← `f8a9b0c1d2e3` |

## Sketch

- `pin_original_access_logs`: id, pin_id, user_id, action (`mint`|`file`), ip, user_agent, created_at  
- Watermark text: `just buy it` — **diagonal** soft tile  
- **Chỉ** apply khi pin `listed`; upload thường = preview sạch; unlist → bỏ watermark  
- Detail: `400 pin_media_incomplete` / `pin_hash_missing`  
- FE Download original: `has_original` thay `pin.original_image`
