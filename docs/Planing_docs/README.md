# Planing_docs — quy ước thư mục

## Vai trò

| Path | Vai trò |
|------|---------|
| `marketplace_jobmarket_feasibility_phase_plan.md` | Explore / khả thi / **phase map + sprint map cấp cao** cho nền chung (Phase 0) và 2 hệ thống. Không thay BR/devplan chi tiết. |
| `deferred_and_out_of_scope_backlog.md` | Backlog **out of scope / defer / admin-later** — ADM-* đang **pull** sang [`admin/`](admin/). |
| `job_market/` | Planning chính Job market (Phase 1.x) — **CLOSED**. |
| `marketplace/` | Planning chính Marketplace (Phase 2.x + 0-market) — **CLOSED**. |
| `admin/` | Planning chính **Admin Ops** (Phase 3.x) — gom UI/ops từ 3 phase trước. |
| `security_followups_type1_type2.md` | Security Type1 fixed / Type2 defer (một phần gắn Admin). |
| `feed_personalization.md` | Home feed P0–P3 CHỐT; embedding/Jina = **P4 defer**. |

## Ranh giới với Implement_docs

- **Planing_docs** = tầm nhìn phase, sprint map, BR cấp hệ thống, quyết định nghiệp vụ dài hạn.
- **Implement_docs** = mỗi **sprint** có thư mục riêng; planning chi tiết + thực thi theo bộ 3 — rule trong `docs/Implement_docs/lessonlearn.md`.

## Luồng chuẩn

```
Planing_docs (phase / sprint map)
        ↓
Implement_docs/<Phase>_SprintN/   ← BR base → Plan #1 → decisions → checklist → code
        ↓
Đóng sprint → cập nhật phase plan + (nếu cần) lessonlearn / issues_history
```

## Trạng thái stream

| Stream | Trạng thái | Ghi chú |
|--------|------------|---------|
| Phase 0-core (Sprint1–3) | **CLOSED** 2026-07-25 | Smoke + manual API test pass |
| Job Market (Phase 1.1–1.6) | **CLOSED** 2026-08-04 | Alembic `b8c9d0e1f2a3` |
| Marketplace (Phase 2.x + 0-market) | **CLOSED** Sprint0–5 2026-08-08 | Head `b4c5d6e7f8a9` |
| Security Type1 hotfix | **DONE** 2026-08-08 | Type2 → security_followups |
| **Admin Ops (Phase 3.x)** | Sprint1–4 **CLOSED** (MVP complete) | [`admin/`](admin/) |
| Home feed personalization | Plan #1 **CHỐT**; Plan #2 OPEN; P4 defer | [`feed_personalization.md`](feed_personalization.md) · [`../Implement_docs/Feed_Sprint1/`](../Implement_docs/Feed_Sprint1/) |

## Sprint đã đóng (Phase 0)

| Sprint | Implement folder | Trạng thái |
|--------|------------------|------------|
| Phase0-Sprint1 (Role & capability) | `docs/Implement_docs/Phase0_Sprint1/` | **CLOSED** 2026-07-25 |
| Phase0-Sprint2 (Ownership & security) | `docs/Implement_docs/Phase0_Sprint2/` | **CLOSED** 2026-07-25 |
| Phase0-Sprint3 (Audit tối thiểu) | `docs/Implement_docs/Phase0_Sprint3/` | **CLOSED** 2026-07-25 |

> **Admin Ops MVP CLOSED** (Sprint1–4). Next initiative theo Planing backlog / product.
