# Base requirement — Feed_Sprint1 (Home personalization P0–P3)

**Input Plan #1.** Prerequisite: soft-live product ổn định; hướng [`../../Planing_docs/feed_personalization.md`](../../Planing_docs/feed_personalization.md) đã CHỐT P0–P3 / defer P4.

## Gaps hiện tại

1. Home = timeline chung theo thời gian đăng — mọi account (và guest) gần như cùng một thứ tự.
2. Recommendation theo tag chỉ đẩy Aside Updates (daily), **không** vào Home feed.
3. Có signal follow / like / save / view và `pin_stats`, nhưng **chưa** dùng để rank Home.
4. Thiếu diversity → dễ bị một author/tag chiếm viewport nếu chỉ sort affinity thô.
5. Embedding / Jina / heavy CF = **P4 defer** (VPS ~4 GiB, 0 swap).

## Mục tiêu sprint

1. Home mặc định = feed personalized (SQL blend): following · tag affinity · explore · trending · fresh.  
2. Pipeline: candidate pools → dedupe → ranker → diversity → feed.  
3. Guest: trending + explore (seed theo ngày).  
4. Opt-out timeline thuần (Everything / mode chrono).  
5. Weights tương tác tập trung (save > like > view), dễ chỉnh sau.  
6. Không embedding API / self-host model.

## Ngoài phạm vi

FEED-P4 (Jina/embed) · multimodal · heavy CF · Firebase · related PinView · đổi Explore JD · redesign UI Home lớn.
