# Deferred & out-of-scope backlog

> **Ngày tạo:** 2026-07-26  
> **Mục đích:** Một chỗ ghi các case / task / feature / chức năng đã **nhắc trong planning** nhưng **không làm trong Job Market Phase 1 implement sắp tới**, hoặc thuộc **admin / làm sau**.  
> **Không** thay SSOT nghiệp vụ Phase 1 — xem [`job_market/business_requirement.md`](job_market/business_requirement.md).  
> Khi mở lại một mục: chuyển sang BR/sprint map tương ứng và đánh dấu đã pull từ file này.

---

## Cách dùng

| Cột | Ý nghĩa |
|-----|---------|
| ID | Mã backlog ổn định |
| Bucket | Nhóm (Admin later / JM later / Never-in-P1 / Marketplace / Hygiene) |
| Nguồn | Chỗ đã chốt / nhắc |
| Gợi ý mở lại | Stream hoặc điều kiện |

---

## A. Admin — có trong phase nhưng UI / luồng đầy đủ để sau

> Phase 1 vẫn cần **API/admin capability tối thiểu** nơi BR bắt buộc (duyệt KYC, moderation cơ bản; admin có thể override credentials). Phần dưới là **Admin UI đầy đủ / vận hành nâng cao**.
>
> **2026-08-08:** Initiative **Admin Ops** đã mở planning tại [`admin/`](admin/) (Phase 0+JM+MP CLOSED). Đánh dấu pull khi Plan #1 CHỐT / từng sprint implement.

| ID | Mục | Ghi chú | Nguồn | Status |
|----|-----|---------|-------|--------|
| ADM-01 | **Admin UI đầy đủ** (dashboard roles, audit viewer, moderation queue UI, KYC review UI hoàn chỉnh) | → Admin Phase 3 shell + queues | Phase 0 / BR out | **pulled → admin/** (system CHỐT; S1 mở) |
| ADM-02 | Admin UI review hiring-rights KYC | → Admin_Sprint2 | BR hiring-rights | **DONE** Admin_Sprint2 |
| ADM-03 | Admin UI credentials override | → Admin_Sprint2 | BR D10 | **DONE** Admin_Sprint2 |
| ADM-04 | Admin UI moderation JD report + suspend | → Admin_Sprint2 | BR §3.E | **DONE** Admin_Sprint2 |
| ADM-05 | Admin UI / workflow **tranh chấp chiếm company** | **Out MVP** (Q5) | BR §3.D | Deferred (admin Later) |
| ADM-06 | Need-more-info KYC UI structured | → Admin_Sprint2 nhẹ | BR §3.D | **DONE** Admin_Sprint2 (note form) |
| ADM-07 | Admin audit log viewer UI | → Admin_Sprint1 | Phase 0 Sprint3 | **pulled → Admin_Sprint1** |
| ADM-08 | Công chứng / notarized translation | **Out MVP** (Q5) | BR §3.D | Deferred (admin Later) |

---

## B. Job Market — defer trong / sau Phase 1 (đã nhắc rõ)

| ID | Mục | Ghi chú | Nguồn |
|----|-----|---------|-------|
| JM-01 | Role **`university`** + luồng approve/verify education giống company | Quá phức tạp, không đáng — **không làm** Phase 1. Credential = owner self-manage, **không** verify bên thứ ba | BR Out of scope; D10 |
| JM-02 | Apply status **`interview`** (và pipeline phỏng vấn) | Chỉ: submitted → viewed → rejected \| passed | BR D8; SAC-07 |
| JM-03 | **Backfill** work-exp khi company mới có tài khoản sau | User tự sửa dòng; hệ thống không auto-link | BR §3.A; D4 |
| JM-04 | Email-token approve work-exp cho company **ngoài** hệ thống | Chỉ in-app approve khi company tồn tại; ngoài hệ thống = luôn chưa approve | BR D4 |
| JM-05 | **Badge verified experience** tổng trên profile | Đi sâu khi planning business riêng; Phase 1 vẫn có status từng dòng | BR D11 |
| JM-06 | Field bổ sung trên **profile gốc** (ngoài tab JM đã mô tả) | Làm sau khi hoàn thành Phase 1 | BR Out of scope; D3 |
| JM-07 | Coi **pins tab** là deliverable Job Market mới | Giữ nguyên tab pin hiện có; không ship như feature JM | BR D3; SAC-01 |
| JM-08 | **Chat gắn application** (`application_id` / deep-link bắt buộc) | Phase 1 đủ apply + notify + profile/CV links; chat optional sau | BR D5 |
| JM-09 | **Multi-member** company (nhiều user quản lý một DN; self-serve “request management rights”) | Phase 1: một ownership sau verify; tranh chấp → admin thủ công | BR §3.D |
| JM-10 | Ranking / recommendation phức tạp cho Explore JD | List default = JD active; filter/search cơ bản thôi | BR §3.B |
| JM-11 | Public gallery / visibility CV kiểu “public profile CV” | CV owner-manage; employer đọc chỉ khi nhận apply | BR D7 |
| JM-12 | Tính CV upload-from-machine (khi apply) vào quota 3 / lưu tab CV | One-shot đính kèm application; **không** vào quota | BR D12 |
| JM-13 | Soft-delete company **tự giải phóng** unique pháp nhân | Không giải phóng key chỉ vì soft delete; cần policy riêng sau | BR §3.D |
| JM-14 | Unique cứng toàn cầu theo `tax_id` / `vat_number` / `website` / `company_name` | Chỉ cảnh báo hoặc rule theo quốc gia sau; khóa chính = legal entity tuple | BR D15 |
| JM-15 | PortfolioView làm nền Job Market | Không dùng | BR rule #6; feasibility plan |

---

## C. Marketplace / Phase 2 — không thuộc Job Market Phase 1

| ID | Mục | Ghi chú | Nguồn |
|----|-----|---------|-------|
| MP-01 | `pins.created_at` + backfill | Eligibility bán | → **Marketplace_Sprint0** (Plan #2 CHỐT) |
| MP-02 | `pin_stats` view bền vững | Eligibility | → **Marketplace_Sprint0** |
| MP-03 | Unique `likes` / `subscriptions` | Chống gian lận follower | → **Marketplace_Sprint0** |
| MP-04 | Watermark / original ACL / signed download | Bản quyền | Marketplace 2.1 |
| MP-05 | Listing bán license + eligibility gate | Marketplace 2.2 | |
| MP-06 | Payment methods / SePay / VNPay / orders | Marketplace 2.3–2.4 | |
| MP-07 | Copyright reports / license certificate | Marketplace 2.5 | |
| MP-08 | Role `seller` behavior đầy đủ | Catalog đã có từ Phase 0; behavior = Marketplace | roles.py / phase plan |

---

## D. Hygiene / platform — song song hoặc sau (không phải feature JM)

> Có thể làm kèm sprint JM khi đụng PII/media; không phải “product feature” trong BR JM.

| ID | Mục | Gợi ý thời điểm | Nguồn |
|----|-----|-----------------|-------|
| HY-01 | Auth + ownership cho `POST /users/upload/{id}` và banner upload | Trước/kèm Sprint có logo/avatar company | Phase 0 handoff |
| HY-02 | Auth SSE updates stream + ownership mark-read updates | Trước/kèm apply notify | Phase 0 handoff |
| HY-03 | Messages upload/read participant check | Khi gắn chat–application (nếu làm JM-08) | Phase 0 handoff |
| HY-04 | `require_roles` OR semantics (employer \| admin) | Khi moderation routes cần | Phase 0 handoff |
| HY-05 | Nới audit action allowlist (migration + CHECK) theo từng mutate JM | Mỗi sprint trust | Phase 0 Sprint3 |
| HY-06 | Vue hydrate `/me/roles`; bỏ hardcode `danya` trên FE | JobMarket Sprint1 hygiene | Phase 0 handoff |
| HY-07 | `POST /users/create-user-entity` unauthenticated | Hygiene sớm | Phase 0 audit |
| HY-08 | CSRF exempt path vs `root_path=/api` trap | Khi thêm exemption thật sự cần | Phase 0 audit |

---

## E. Never / explicit reject trong Phase 1 (nhắc để khỏi hỏi lại)

| ID | Mục | Lý do |
|----|-----|-------|
| NO-01 | Quay lại Phase 0 để thêm role `university` trước JM | Scope creep; credential = owner CRUD, không university approve |
| NO-02 | DRM / chống copy file tuyệt đối (Marketplace) | Không khả thi như đã ghi feasibility |
| NO-03 | UNIQUE(company_name) hoặc UNIQUE(website_domain) làm hard block pháp nhân | False positive; chỉ warning |
| NO-04 | Tiết lộ danh tính requester khi company đang pending verification khác | Privacy |
| NO-05 | Ship payment / watermark trong Job Market stream | Thứ tự: JM rồi Marketplace |

---

## F. Checklist khi pull mục từ backlog này

1. Cập nhật BR hệ thống hoặc BR sprint tương ứng.  
2. Thêm/ sửa dòng trên `job_market/sprint_map.md` hoặc `marketplace/` map.  
3. Đánh dấu ID trong file này: `Status: pulled → <path> (<date>)`.  
4. Không implement chỉ vì có mặt trong backlog.

---

## G. Security follow-ups (Type 2 — defer)

> Index đầy đủ: [`security_followups_type1_type2.md`](security_followups_type1_type2.md). Type 1 đã fix 2026-08-08.

| ID | Mục | Gợi ý mở lại |
|----|-----|--------------|
| SEC-T2-01 | Copyright resolve → unlist / revoke license | **DONE** unlist (Admin_Sprint3); revoke vẫn later |
| SEC-T2-02 | Rate-limit copyright reports | **DONE** Admin_Sprint3 (`MP_COPYRIGHT_REPORT_MAX`) |
| SEC-T2-03 | `PIN_MEDIA_SIGNING_SECRET` bắt buộc tách JWT | Media hardening |
| SEC-T2-04 | Strip `original_image` khỏi public PinOut | **DONE** Marketplace_Sprint7 |
| SEC-T2-05 | KYC/CV magic-byte + page limits | JobMarket upload harden |
| SEC-T2-06 | Policy dual seller+employer | BR product |
| SEC-T2-07 | VNPay / auto payout / chargeback | Manual/stub payout **DONE** Sprint8; live Open API → T2-S8-01 |
| SEC-T2-08 | Admin UI product | **pulled → [`admin/`](admin/)** (draft Plan #1); payout queue **DONE** Sprint8 |
| SEC-T2-S8-01 | Live Open Banking disbursement | Marketplace_Sprint8 SECURITY_FOLLOWUPS |
| SEC-T2-S8-02 | eKYC / micro-deposit STK | Post-volume |
| SEC-T2-S8-03 | Auto cron payout | After live provider |

---

## H. Liên kết

| Doc | Vai trò |
|-----|---------|
| [`job_market/business_requirement.md`](job_market/business_requirement.md) | SSOT in-scope Phase 1 |
| [`job_market/sprint_map.md`](job_market/sprint_map.md) | Cắt sprint (sẽ sync sau file này) |
| [`marketplace/`](marketplace/) | Stream Phase 2 |
| [`security_followups_type1_type2.md`](security_followups_type1_type2.md) | Type1 fixed / Type2 defer |
| [`marketplace_jobmarket_feasibility_phase_plan.md`](marketplace_jobmarket_feasibility_phase_plan.md) | Phase map cấp cao |

---

*Seeded 2026-07-26 từ BR Job Market D1–D16, Phase 0 handoff, và các phiên chốt apply / KYC / legal-entity. §G security Type2 thêm 2026-08-08.*
