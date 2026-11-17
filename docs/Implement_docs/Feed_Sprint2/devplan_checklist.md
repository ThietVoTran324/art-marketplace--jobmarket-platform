# Devplan checklist — Feed_Sprint2

**Plan #2 CHỐT** 2026-11-17. Prove local **DONE** 2026-11-17.

## Home login

- [x] Config: cap 400, affinity 90 ngày / top 5 tag, trending 48 giờ, penalty author/tag (`feed_config.py`)
- [x] Pool SQL following / affinity / explore / trending / fresh + bù pin mới (`feed_ranker.py`)
- [x] Decay theo giờ, tag IDF, trending = view/giờ trong 48 giờ
- [x] `feed_nonce` chỉ trộn jitter login; guest bỏ qua
- [x] Diversity mềm + streak cứng
- [x] Demote save gần đây / đã xem giữ nguyên

## Related

- [x] `GET /api/tags/{pin_id}`: overlap × Wilson → co-save limit → author mọi tag trần 4 → random trần 8
- [x] View 0 không chia 0
- [x] Không bảng mới

## FE

- [x] HomeView gửi `feed_nonce` cho `mode=home`, một nonce cho cả scroll

## Giữ nguyên

- [x] Guest popularity trên cửa sổ pin mới
- [x] `mode=chrono` không dùng nonce
- [x] Không gọi model / embed trong request feed

## Prove-done

Local 2026-11-17: 3 pin, 1 user, không có `board_pins`. API + gọi ranker trong container.

- [x] Login home: hai nonce khác nhau đổi thứ tự; cùng nonce hai trang không trùng pin
- [x] `mode=chrono` = 3, 2, 1
- [x] Guest home 200, nonce `aaa` và `bbb` cùng thứ tự
- [x] Related: pin 1 → 3 rồi 2; pin 2 → 3 rồi 1; pin 3 → 1 rồi 2 (Jaccard). Co-save chạy nhưng catalog không có board
- [x] Route search và tag browse không sửa; guest gọi related/tag vẫn 401 như trước
