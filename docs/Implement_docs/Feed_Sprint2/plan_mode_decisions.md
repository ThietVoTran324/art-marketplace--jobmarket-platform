# Plan mode decisions — Feed_Sprint2

> **Plan #2 CHỐT** 2026-11-17 — `all suggest` (T1–T12 = A).
> BR: [business_requirement.md](business_requirement.md)

## Meta

| | |
|---|---|
| Initiative | Home multi-pool + Related nhẹ |
| Baseline | Feed_Sprint1 ranker (newest window + flat boosts); Related 4 bucket cũ |
| Migrate | **Không** |

## Quyết định kỹ thuật

| ID | CHỐT |
|----|------|
| T1 | Candidate ~400, chia theo `FEED_POOL_RATIOS` (following / affinity / explore / trending / fresh). Pool mỏng thì bù pin mới. |
| T2 | Affinity 90 ngày trên save (có timestamp). Like/view không có mốc thời gian — lấy có trần, rồi giữ top 5 tag. |
| T3 | Trending = pin tạo trong 48 giờ, cộng điểm theo view / giờ (không có log view theo giờ nên không làm HN gravity). |
| T4 | Explore = pin có tag chính ngoài top tag của user, số lượng có trần. |
| T5 | `feed_nonce` trên `GET /api/pins/?mode=home`. FE tạo một lần khi load/F5, giữ nguyên khi scroll. Chrono bỏ qua. Guest bỏ qua. |
| T6 | Trừ điểm khi pick trùng author/tag; streak cứng (author 2, tag 3) vẫn là chặn cuối. |
| T7 | Trọng số tag nhân `1/log(1+số pin mang tag)`, chỉ trên candidate. |
| T8 | Related: trùng tag (Jaccard × Wilson) → co-save giới hạn → cùng author mọi tag (trần nhỏ) → random nhỏ. |
| T9 | Wilson lower bound like/view. View = 0 thì hạng thấp, không chia 0. |
| T10 | Co-save = query `board_pins` sẵn có, limit nhỏ. Không bảng mới, không job đêm. |
| T11 | Không migration. |
| T12 | Guest popularity và `mode=chrono` giữ nguyên. |

## Out

CLIP/SigLIP, CF đêm, Gemini cho feed, BM25 đầy đủ, FEED-P4 / P4b / P4c, đổi search, đổi Aside `make_user_recommendations`.
