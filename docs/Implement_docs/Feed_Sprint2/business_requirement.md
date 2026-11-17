# Business Requirements — Feed_Sprint2

**Mức chi tiết:** ~3/10 (business). Hằng số / query → Plan #2.  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Prereq:** [`../Feed_Sprint1/`](../Feed_Sprint1/) (Home SQL blend đã ship) · VPS nhẹ · không model embed  
**Hướng:** [`../../Planing_docs/feed_personalization.md`](../../Planing_docs/feed_personalization.md) — **không** kéo FEED-P4

> **Plan #1 CHỐT** 2026-11-17 — **all suggest** (S1–S12 = A).

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Home login lấy ứng viên từ **nhiều nguồn** (follow, tag yêu thích cửa sổ dài, trending ngắn, khám phá tag lạ, fresh) — không chỉ dải pin mới nhất |
| 2 | Điểm xếp hạng suy giảm theo tuổi pin; tag ngách nặng hơn tag phổ biến |
| 3 | Reload / phiên mới có thể đổi thứ tự; cuộn trong cùng phiên giữ thứ tự |
| 4 | Đa dạng bằng phạt nhẹ cùng tác giả / cùng chủ đề khi chọn lần lượt |
| 5 | Related (cột phải + lưới dưới detail) ưu tiên trùng tag và pin hay lưu cùng; hạ “mọi pin của cùng tác giả”; chất lượng theo tỷ lệ tương tác |
| 6 | Timeline thuần (`chrono`) và guest popularity **giữ** |
| 7 | Không model, không embed, không job ma trận đêm |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| User login | Home cá nhân + related sát pin đang xem |
| Guest | Home popularity như Feed_Sprint1 |
| Hệ thống | Truy vấn + chấm điểm trong request, trần ứng viên nhỏ |

---

## 3. Quy tắc CHỐT (S1–S12 = A)

| ID | CHỐT |
|----|------|
| C1 | Một sprint: **Home + Related** (S1 A) |
| C2 | Home login: nhiều pool theo tỷ lệ đã có, trần ứng viên nhỏ (S2 A) |
| C3 | Affinity: save/like/view, cửa sổ dài (~90 ngày), số tag top có hạn (S3 A) |
| C4 | **Không** lọc cộng tác user–user / item–item đêm (S4 A) |
| C5 | Jitter theo phiên hoặc lần reload; phân trang trong phiên ổn định (S5 A) |
| C6 | Đa dạng: phạt điểm cùng tác giả/chủ đề (S6 A) |
| C7 | Tag phổ biến được giảm trọng số bằng công thức đơn giản (S7 A) |
| C8 | Related: “cùng tác giả mọi tag” hạ cuối và giới hạn số (S8 A) |
| C9 | Related: chất lượng theo tỷ lệ tương tác, không tổng like thô (S9 A) |
| C10 | Nguồn “lưu chung” = truy vấn giới hạn trên board hiện có — không job đêm (S10 A) |
| C11 | Không vision / CLIP / Gemini cho hai luồng (S11 A) |
| C12 | Guest home giữ popularity (S12 A) |
| C13 | `chrono` vẫn timeline mới nhất |
| C14 | Search, duyệt tag, Aside recommend không đổi hành vi |

---

## 4. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Hai user khác lịch sử → thứ tự Home khác nhau quan sát được |
| AC-02 | Reload / phiên mới có thể đổi thứ tự; cuộn tiếp cùng phiên không đảo trang đã xem |
| AC-03 | Home có pin ngoài dải “chỉ mới nhất” (follow hoặc tag yêu thích) |
| AC-04 | Không chuỗi dài cùng tác giả hoặc cùng chủ đề |
| AC-05 | `chrono` vẫn mới nhất như cũ |
| AC-06 | Related ưu tiên trùng tag / lưu chung; không lấp sớm bằng mọi pin của tác giả |
| AC-07 | Pin tỷ lệ tương tác cao có thể xếp trên pin like thô rất lớn |
| AC-08 | Search, tag browse, Aside recommend không regress |
| AC-09 | Request Home/Related không gọi model embed/vision |
| AC-10 | Guest home vẫn trả được, không 500 khi ít dữ liệu |

---

## 5. Out of scope

| ID | Out |
|----|-----|
| FEED-P4 / P4b / P4c | Embed, visual, self-host model, CF nặng |
| N-gemini-feed | Gemini cho feed/related |
| N-bm25-full | TF-IDF/BM25 corpus đầy đủ |
| N-cosave-job | Bảng co-occurrence + job đêm |
| N-search-change | Đổi search / tag browse |
| N-aside | Đổi Aside daily recommendations |

---

## 6. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)  
- [README.md](README.md)  
