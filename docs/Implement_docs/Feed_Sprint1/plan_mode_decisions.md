# Plan mode decisions — Feed_Sprint1

> **Plan #2 CHỐT** 2026-10-08 — `all suggest` từ quiz chat.  
> BR: [business_requirement.md](business_requirement.md)

## Meta

| | |
|---|---|
| Initiative | Feed_Sprint1 — Home SQL blend P0–P3 |
| Baseline | `GET /api/pins/` order `id` desc; signals: subscriptions, likes, board_pins, users_view_pins, pin_stats, pins_tags |
| Migrate | **Không** bảng mới (Q6A) |

## Quyết định kỹ thuật

| ID | CHỐT |
|----|------|
| Q1 | `GET /api/pins/?mode=home\|chrono` — default `home` (login + guest lite); `chrono` = timeline cũ |
| Q2 | Pool ratios (login): following 30% · affinity 35% · explore 15% · trending 10% · fresh 10% (theo page size) |
| Q3 | Diversity: max **2** cùng author liên tiếp; max **3** cùng primary tag liên tiếp |
| Q4 | `INTERACTION_WEIGHTS = {save: 3.0, like: 2.0, view: 1.0}` một module config |
| Q5 | View/save **7 ngày**: hard exclude nửa đầu page 1; soft demote sau đó |
| Q6 | Không migrate / không impression table |
| Q7 | FE HomeView: personalized mặc định; chrono khi Everything hoặc `mode=chrono` |
| Q8 | Rank in-request; candidate cap ~200–400; không materialize hourly |

## Out

FEED-P4 · Related PinView · đổi search/tag APIs.
