# Business Requirements — Feed_Sprint1 (Home personalization P0–P3)

**Mức chi tiết:** ~3/10 (business). Route/schema/weights code → Plan #2.  
**SSOT hướng:** [`../../Planing_docs/feed_personalization.md`](../../Planing_docs/feed_personalization.md)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)

> **Plan #1 CHỐT** 2026-10-08 — `all suggest` + override AC-02, AC-05 (pipeline), AC-18 (weights tập trung).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Home mặc định cá nhân hóa theo account (và guest lite), không chỉ timeline chung |
| 2 | Candidate pools: Following · Tag affinity · Explore · Trending · Fresh → dedupe → rank → diversity |
| 3 | Opt-out timeline thuần (Everything / mode chrono) |
| 4 | Exclude/deprioritize pin vừa xem/save gần đây khỏi đầu feed |
| 5 | Affinity dùng signal save > like > view với trọng số cấu hình tập trung |
| 6 | Aside daily recommendations giữ nguyên; đồng thời affinity vào Home |
| 7 | Không embedding / 3rd-party recommend / self-host model (P4) |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| Guest | Home = trending + explore (seed theo ngày UTC); không affinity cá nhân |
| User login | Home blend đủ pools; diversity; cold-start nếu thiếu signal |
| Hệ thống | Rank + phân trang; fallback an toàn nếu thiếu data |

---

## 3. Quy tắc (CHỐT Plan #1)

| ID | CHỐT |
|----|------|
| S1 | Một sprint `Feed_Sprint1` gói P0–P3 |
| S2 | Timeline cũ: mode **chrono** + tag Everything vẫn timeline thuần |
| S3 | Guest: trending + explore (seed ngày); **không** giữ chỉ `id` desc làm mặc định guest |
| S4 | Exclude/deprioritize bằng signal view/save gần đây có sẵn — **không** bắt buộc bảng impression mới |
| S5 | Giữ Aside Updates recommend; **và** đưa affinity vào Home |
| S6 | Related PinView **out** sprint |
| D-pipe | Pipeline bắt buộc: Candidate pools (Following / Tag affinity / Explore / Trending / Fresh) → Deduplicate → Ranker → Diversity → Feed |
| D-w | Trọng số tương tác tập trung (một chỗ cấu hình): save > like > view; gợi ý tương đối 3 / 2 / 1 — chi tiết hằng số Plan #2 |

---

## 4. Acceptance criteria

| AC | Phase | Mô tả |
|----|-------|-------|
| AC-01 | P0 | User login mở Home (mode mặc định) không chỉ nhận timeline chung giống mọi account |
| AC-02 | P0 | Với hai user có interaction history khác biệt đáng kể, ranking của các item liên quan tới affinity của từng user phải có sự khác biệt có thể quan sát được |
| AC-03 | P0 | Cùng user, cùng ngày UTC: mix ổn định có chủ đích (seed user+ngày), không random mỗi request |
| AC-04 | P0 | Đổi ngày UTC có thể đổi mix |
| AC-05 | P0 | Candidate pool gồm Following · Tag affinity · Explore · Trending · Fresh; sau đó Deduplicate → Ranker → Diversity → Feed |
| AC-06 | P0 | Cold-start login (ít/không follow·like·save): Home vẫn hợp lệ, nghiêng explore/trending — không trống / không 500 |
| AC-07 | P0 | Guest nhận trending + explore (seed ngày); không bắt login |
| AC-08 | P0 | Guest không dùng lịch sử user khác; không lộ private |
| AC-09 | Opt-out | Có timeline thuần (Everything và/hoặc mode chrono) = mới nhất như cũ |
| AC-10 | Opt-out | Timeline thuần không gãy phân trang / infinite scroll |
| AC-11 | P1 | Affinity/recommend theo tag xuất hiện trong Home, không chỉ Aside |
| AC-12 | P1 | Aside daily recommendations vẫn hoạt động |
| AC-13 | P1 | Pin vừa xem/save gần đây loại hoặc hạ thứ tự khỏi phần đầu feed |
| AC-14 | P1 | Self-pin không spam đầu feed |
| AC-15 | P2 | Không chuỗi dài cùng author liên tiếp vượt ngưỡng diversity (số N → Plan #2; hướng 2–3) |
| AC-16 | P2 | Không chuỗi dài cùng tag chủ đạo liên tiếp vượt ngưỡng tương tự |
| AC-17 | P2 | Có inject fresh + popular gần đây (~7 ngày hướng) |
| AC-18 | P3 | Trọng số tương tác **tập trung một nơi cấu hình** (tránh rải rác trong ranker); thứ tự save > like > view; tương đối gợi ý save=3, like=2, view=1 |
| AC-19 | P3 | Cold-start guest vs login khác nhau rõ |
| AC-20 | Cross | Phân trang/load thêm không lặp vô hạn cùng tập nhỏ trang đầu |
| AC-21 | Cross | Tag browse (ngoài Home personalized) + search pins không regress |
| AC-22 | Cross | PinView / create / boards / marketplace / JM không đổi ngoài thứ tự Home |
| AC-23 | Cross | Không embedding API; không self-host model |
| AC-24 | Cross | Lỗi/missing signal → fallback an toàn; không 500 hàng loạt Home / feed-meta |

---

## 5. Out of scope

FEED-P4 (Jina/embed) · multimodal · heavy CF · Firebase · Related PinView · Explore JD ranking · redesign UI Home lớn.

---

## 6. Sync

- [`../../Planing_docs/feed_personalization.md`](../../Planing_docs/feed_personalization.md) — Plan #1 CHỐT pointer  
- Backlog P4: [`../../Planing_docs/deferred_and_out_of_scope_backlog.md`](../../Planing_docs/deferred_and_out_of_scope_backlog.md) §I  
