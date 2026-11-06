# Feed Search Wave1 — perf follow-ups (note, chưa CHỐT implement)

> Bối cảnh 2026-11-06: BE search warm ~10 ms; cảm giác ~2s = **tải ảnh preview** (N × `/pins/upload/{id}`).  
> Security Type2: [`SECURITY_FOLLOWUPS.md`](SECURITY_FOLLOWUPS.md).

---

## A. Đề xuất trước (media / cache) — defer

| ID | Đề xuất | Tác động cảm giác 2s | Ghi chú |
|----|---------|----------------------|---------|
| PERF-A | Warm Redis top tag / popular `q` → pin ids | Thấp (BE đã đủ nhanh) | Cron/materialize |
| PERF-B | Prefetch 6–10 ảnh đầu sau Enter (`Image()` / link rel) | Cao (above-fold) | An toàn: vẫn qua `/pins/upload/{id}` |
| PERF-C | Materialize popular q → first N ids offline | Thấp–TB | Giống recommend list |
| PERF-D | Thumbnail nhỏ hơn / WebP | **Cao nhất** (ít byte) | Media pipeline |
| PERF-E | Tận dụng HTTP cache ảnh (đã `max-age=3600`) | Chỉ khi trùng pin id với feed | Đã ship |

---

## B. Đề xuất product (windowing / scroll) — review 2026-11-06

### B1. Windowing: chỉ render đủ **1 viewport** lúc Enter

- **Ý:** Kết quả bao nhiêu cũng chỉ fetch/render lượng pin lấp đầy màn hình ban đầu; kéo xuống mới lấy dãy tiếp (10–20). Kéo sớm mà chưa có page sau → chấp nhận trống/skeleton ngắn.
- **Số “10 pin / 1 màn” có đúng không?**  
  - Grid hiện tại: `grid-cols-2 … lg:grid-cols-5`, card `aspect-[3/4]`, thêm header + tag bar.  
  - Desktop rộng: thường **~8–15** pin/viewport (vd. 5 cột × 2 hàng ≈ 10; 5×3 ≈ 15).  
  - Mobile: **~4–8**.  
  - **Hardcode 10 không đúng mọi máy** — chỉ là default hợp lý gần đúng trên desktop.
- **Linh động:** Nên tính / truyền `pageSize` (hoặc lặp `fillViewportIfNeeded` như home feed) theo viewport, không cố định 10 trong product rule. Home feed đã có pattern `fillViewportIfNeeded` + sentinel; **PinsBySearch chưa có** (chỉ scroll gần đáy + first limit 10 rồi 5).

### B2. Trigger cuộn giống feed chính

- **Feed chính hiện tại:**  
  - Tải **chỉ tiến** (xuống đáy / sentinel `rootMargin: 600px`).  
  - **Không** xóa pin khỏi DOM khi scroll xa; **không** virtualize ngược.  
  - `PinFeedCard` chỉ **lazy src ảnh** (IntersectionObserver) — component vẫn mount.
- **Search hiện tại:** scroll `+200px` đáy → `loadPins`; không sentinel; không unmount.
- **Đề xuất “scroll xa → xóa DOM, scroll lên → render lại”:** đây là **window/virtual list mới**, **chưa có** trên feed chính. Effort + rủi ro (scroll jump, like state, IO) cao hơn B1. Nên tách:  
  - **B2a (nên làm cùng windowing):** forward infinite + fillViewport + sentinel như home.  
  - **B2b (sau):** bidirectional recycle DOM / virtualizer.

### B3. Blur / placeholder

- **Đã có:** pulse placeholder trên card đến khi `mediaVisible` + `loading="lazy"`.  
- Dùng lại; không cần hệ placeholder mới cho Wave1 perf.

### B4. Pagination BE search

- **Đã có sẵn:** `GET /api/pins/search?offset=&limit=&value=` (`FilterWithValue`, `limit` 1…100). Redis cache theo `offset:limit`.  
- FE `PinsBySearch` đã gọi `offset`/`limit` (10 rồi 5).  
- Việc còn lại: **đồng bộ `limit` lần đầu = pageSize viewport** (B1), không phải viết pagination BE mới.

---

## C. Verdict agent (đề xuất user)

| Đề xuất | OK? | Điều chỉnh |
|---------|-----|------------|
| Windowing 1 màn hình | **OK** | Đừng hardcode 10; `pageSize` linh động / fillViewport |
| Chấp nhận thiếu page sau nếu kéo sớm | **OK** | Skeleton ngắn đủ |
| Trigger giống feed (tới / qua đáy) | **OK** | Align sentinel + fillViewport |
| Xóa DOM khi scroll xa / tải lại khi lên | **OK về ý** nhưng **scope lớn hơn** feed hiện tại → B2b sau |
| Dùng blur/placeholder sẵn | **OK** | Giữ |
| Pagination BE | **Đã có** | Chỉ chỉnh FE pageSize |

**CHỐT implement 2026-11-06:** B1 + B2a + B3 (reuse) + B4 (FE limit) + PERF-B.  
**DROP / defer:** B2b virtualize; PERF-A/C (Redis warm); **PERF-D** WebP/thumb encode (giữ chất lượng preview/detail; không đổi `generate_pin_preview`).

---

## D. Không nhầm với Redis

Catch Redis search (resolve + pin ids, TTL 45–60s) **không** thay windowing/ảnh. Warm Redis (PERF-A/C) gần như không đổi cảm giác ~2s.

---

## E. Risk probe sau implement windowing + prefetch (2026-11-06)

| Case | Kết quả |
|------|---------|
| Đụng `generate_pin_preview` / chất lượng detail | **Không** — cùng `/pins/upload/{id}`; PinView blob path riêng |
| Prefetch URL khác card | **Không** — `pinPreviewUrl` chung; browser HTTP cache |
| `limit` vượt BE | Clamp estimate ≤20 first page; hint ≤100; BE `le=100` |
| fillViewport loop | Chặn `isPinsLoading` / `hasMore` (giống home) |
| Prefetch Set module-level lớn dần | Type2 nhẹ (session dài); URL public preview OK |
| Virtualize scroll-up | Không làm (DROP) |
