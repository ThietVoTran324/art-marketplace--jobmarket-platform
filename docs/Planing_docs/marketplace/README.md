# Marketplace — planning chính

> Hệ thống **bán license pin** + SePay (VNPay sau) + watermark / original ACL.  
> **Thứ tự:** sau Phase 0-core và Job Market Phase 1 **CLOSED**.  
> **Numbering:** Phase **0-market** + Phase **2.1–2.8**.  
> Nguồn: [`../marketplace_jobmarket_feasibility_phase_plan.md`](../marketplace_jobmarket_feasibility_phase_plan.md).

## Mục lục

| File | Vai trò |
|------|---------|
| [README.md](README.md) | Index |
| [phase0_market_and_block_classification.md](phase0_market_and_block_classification.md) | Block 0-market + điểm khó |
| [system_survey.md](system_survey.md) | Codebase gaps |
| [business_requirement.md](business_requirement.md) | SSOT nghiệp vụ hệ thống — **Plan #1 CHỐT** |
| [sprint_map.md](sprint_map.md) | Sprint0–8 — **Synced** |
| [`../deferred_and_out_of_scope_backlog.md`](../deferred_and_out_of_scope_backlog.md) | MP-* / no refund / no DRM |

## Implement_docs (template)

| Folder | Phase | Plan status |
|--------|-------|-------------|
| [`../../Implement_docs/Marketplace_Sprint0/`](../../Implement_docs/Marketplace_Sprint0/) | 0-market | **CLOSED** 2026-08-08 · Alembic `c9d0e1f2a3b4` |
| [`../../Implement_docs/Marketplace_Sprint1/`](../../Implement_docs/Marketplace_Sprint1/) | 2.1 Media | **CLOSED** 2026-08-08 · `d0e1f2a3b4c5` |
| [`../../Implement_docs/Marketplace_Sprint2/`](../../Implement_docs/Marketplace_Sprint2/) | 2.2 Listing | **CLOSED** 2026-08-08 · `e1f2a3b4c5d6` |
| [`../../Implement_docs/Marketplace_Sprint3/`](../../Implement_docs/Marketplace_Sprint3/) | 2.3 Payout method | **CLOSED** 2026-08-08 · `f2a3b4c5d6e7` |
| [`../../Implement_docs/Marketplace_Sprint4/`](../../Implement_docs/Marketplace_Sprint4/) | 2.4 SePay order | **CLOSED** 2026-08-08 · `a3b4c5d6e7f8` |
| [`../../Implement_docs/Marketplace_Sprint5/`](../../Implement_docs/Marketplace_Sprint5/) | 2.5 Copyright | **CLOSED** 2026-08-08 · `b4c5d6e7f8a9` |
| [`../../Implement_docs/Marketplace_Sprint6/`](../../Implement_docs/Marketplace_Sprint6/) | 2.6 Verify + SePay live | **CLOSED** 2026-09-27 · `e7f8a9b0c1d2` |
| [`../../Implement_docs/Marketplace_Sprint7/`](../../Implement_docs/Marketplace_Sprint7/) | 2.7 Media evidence | **CLOSED** 2026-09-28 · `a9b0c1d2e3f4` |
| [`../../Implement_docs/Marketplace_Sprint8/`](../../Implement_docs/Marketplace_Sprint8/) | 2.8 Seller payout | **CLOSED** 2026-09-28 · `b0c1d2e3f4a5` |

Mỗi folder: `PLANNING_TRIO.md` · `base requirement.md` · `business_requirement.md` · `plan_mode_decisions.md` · `devplan_checklist.md`.

## Quyết định hệ thống D1–D10

| ID | CHỐT |
|----|------|
| D1 | License 1 lần / pin · personal use |
| D2 | Payout STK/ví; không ví nội bộ; hoa hồng % config |
| D3 | Watermark static |
| D4 | N=5 · M=100 · K=10 + payment method |
| D5 | Pass gate → role `seller` |
| D6 | SePay-first |
| D7 | **Không** refund/return trong hệ thống |
| D8 | VND + USD · **USD mặc định** |
| D9 | Email verified; không tự mua pin mình |
| D10 | Pin cũ ít → **được xóa** nếu conflict pipeline mới |

## Trạng thái

| Hạng mục | Status |
|----------|--------|
| Plan #1 BR hệ thống | **CHỐT** 2026-08-08 |
| Sprint map | **Synced** |
| Implement Sprint0 | **CLOSED** · `c9d0e1f2a3b4` |
| Implement Sprint1 | **CLOSED** · `d0e1f2a3b4c5` · smoke PASS |
| Implement Sprint2 | **CLOSED** · `e1f2a3b4c5d6` · smoke PASS |
| Implement Sprint3 | **CLOSED** · `f2a3b4c5d6e7` · smoke PASS |
| Implement Sprint4 | **CLOSED** · `a3b4c5d6e7f8` · smoke PASS |
| Implement Sprint5 | **CLOSED** · `b4c5d6e7f8a9` · smoke PASS |
| Implement Sprint6 | **CLOSED** · `e7f8a9b0c1d2` · smoke PASS |
| Implement Sprint7 | **CLOSED** · `a9b0c1d2e3f4` · smoke PASS |
| Implement Sprint8 | **CLOSED** · `b0c1d2e3f4a5` · smoke PASS |
| Phase 2.x map | Sprint0–8 **COMPLETE** |
| Next | Live Open API payout (Type2) khi sẵn sàng |
