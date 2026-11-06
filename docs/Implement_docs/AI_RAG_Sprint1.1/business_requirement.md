# Business Requirements — AI_RAG_Sprint1.1 (Plan A)

**Mức chi tiết:** ~3/10 (business). Schema/API → Plan #2.  
**Prereq:** [`../AI_RAG_Sprint1/`](../AI_RAG_Sprint1/) FAQ RAG + [`../AI_Chat_Sprint2/`](../AI_Chat_Sprint2/)  
**Index:** [PLANNING_TRIO.md](PLANNING_TRIO.md)  
**Follow-ups:** [`../AI_RAG_Sprint1/RAG_FOLLOWUPS.md`](../AI_RAG_Sprint1/RAG_FOLLOWUPS.md)

> **Plan #1 CHỐT** 2026-11-06 — `1A 2C′ 3A 4A+intent-tags 5–7A` + rest suggest.  
> Đánh giá hướng Intent→Tags: xem §4.

---

## 1. Mục tiêu

| # | Năng lực |
|---|----------|
| 1 | Index **pin text** (title + description + tags) vào RAG — parent/child |
| 2 | **Semantic + parent–child** chunk (parent = pin; child = đoạn) |
| 3 | **Hybrid** vector + keyword → **RRF** |
| 4 | **Intent → predicted tags → khớp tag hệ thống** (structured JSON, read-only) rồi lọc/rank pin — **không** retag/ghi tag |
| 5 | Cite pin url + thumb; SQL listed/orders **giữ**; FAQ RAG Sprint1 không regress |

---

## 2. Actors

| Actor | Hành vi |
|-------|---------|
| User login | Hỏi tìm ảnh / vibe / “ảnh chill…” → intent-tags + hybrid retrieve; how-to vẫn FAQ |
| Hệ thống | Offline: embed pin chunks + **embed catalog tags**; reindex khi pin/tag đổi |
| Chatbot | **Cấm** gọi auto-tag / retag / ghi `pins_tags` |

---

## 3. Quy tắc CHỐT

| ID | CHỐT |
|----|------|
| A1 | Scope = pin-text + semantic/parent-child + hybrid RRF + **intent→tags bridge** |
| A2 | Corpus pin: **title + description + tag names hiện có** (public). `incorrect_tags` = log auto-tag **không** đưa vào index RAG (xem §4.2) |
| A3 | Parent = 1 pin; Child = đoạn (title / desc đoạn / nhóm tag); retrieve child → cite **parent pin** |
| A4 | Semantic chunk nhẹ; FAQ dài có thể refine — không Vision-OCR |
| A5 | Hybrid vector + keyword + RRF |
| A6 | SQL skills listed/search/orders **giữ**; RAG + intent-tags **bổ sung** |
| A7 | Offline backfill/reindex; không embed cả kho mỗi câu chat |
| A8 | Chỉ pin **public** |
| A9 | Cite pin absolute url + thumb (Sprint2) |
| A10 | Intent-tags: structured output 1–4 tags; empty nếu rác; **luôn English kebab-case** dù user hỏi **bất kỳ ngôn ngữ** (VI/EN/…); khớp chuẩn auto-tag; rồi vector-match catalog → SQL/rank |
| A11 | Skill mới tên riêng (`predict_search_tags` / tương đương) — **không** tái dụng / gọi pipeline retag |
| A12 | Out: Vision-OCR · FAQ CMS · Jina bắt buộc · JD · LangChain bắt buộc · mutate · vision-scan-all · open ChatGPT |

---

## 4. Đánh giá hướng Intent→Tags (user) — giữ / sửa / bỏ

### 4.1 Giữ (tốt)

| Phần | Lý do |
|------|--------|
| Structured JSON (`reasoning` + `predicted_tags`) | Giống auto-tag; dễ parse; học JD |
| Max 1–4 tags | Chống rác / cost |
| Slang → mood/state chuẩn | Vá “chill / suy / healing” |
| Empty `[]` khi vô nghĩa | Tránh crash / filter sai |
| Bước 2: embed predicted ↔ **catalog tag** + ngưỡng config | Đồng nghĩa / lệch wording |
| Bước 3: SQL + ranking quanh tag khớp | Tận dụng index tag đã có |

### 4.2 Sửa (bắt buộc)

| Vấn đề | Sửa CHỐT |
|--------|----------|
| Prompt ví dụ ra tag **tiếng Việt** + `_` | Hệ thống tag = **English kebab-case**. Predicted **bắt buộc English** dù input VI/EN/lóng (`sports-car`, `red`, `lonely`, `hanoi`, …). Prompt ghi rõ: *any user language → English tags only*. Normalize giống `normalize_tag_name` |
| “Dùng chung skill retag” | **Không** — retag = ghi DB / cấm chatbot. Skill **read-only** tên mới |
| Q2 C “incorrect_tags vào corpus” | **Không index** `incorrect_tags` vào RAG (nhiễu search). Pin index chỉ tag **đang gắn**. incorrect_tags giữ audit auto-tag |
| Chỉ Intent-tags **thay** hybrid/parent-child | **Không thay** — Intent-tags = nhánh discovery; hybrid RAG vẫn cho paraphrase trên title/desc |

### 4.3 Bỏ / không làm trong 1.1

| Bỏ | Lý do |
|----|--------|
| Sinh tag tiếng Việt rồi dịch sau | Dễ lệch catalog; làm English ngay |
| Ghi / tạo tag mới từ predicted vào DB | Mutate + bẩn catalog |
| Vision/OCR trong intent | Out A |
| Gọi Celery auto-tag từ chat | N-autotag-chat |

### 4.4 Nâng cấp gợi ý (Plan #2 chi tiết)

- Few-shot case giữ, nhưng output English kebab-case.  
- Precompute embed **toàn bộ tag names** (job); query chỉ embed 1–4 predicted.  
- Sau match: intersection với tag thật → filter pin; có thể **RRF** với nhánh vector pin-text.  
- Nếu predicted rỗng → fallback hybrid retrieve / `search_pins`, không ép filter tag.

---

## 5. Acceptance criteria

| AC | Mô tả |
|----|--------|
| AC-01 | Pin public được index (title/desc/tags); reindex/backfill chạy được |
| AC-02 | Parent–child: hit child → cite/trả parent pin (+ url/thumb) |
| AC-03 | Hybrid + RRF: exact tag/title và paraphrase đều có đường thắng hợp lý |
| AC-04 | Intent “ảnh chill / thất tình…” → predicted English tags → khớp catalog → pin liên quan; rác → `[]` + fallback |
| AC-05 | Không ghi tag / không retag / không vision-scan-all |
| AC-06 | Listed/orders SQL skills không regress; FAQ retrieve không regress |
| AC-07 | incorrect_tags không xuất hiện như “nội dung tìm được” từ RAG index |

---

## 6. Out of scope

| ID | Out |
|----|-----|
| N-rag-doc-vision-ocr | Vision/OCR bảng+caption |
| N-rag-faq-cms / admin-reindex-ui / jina-live / jd-text | Sau A |
| N-framework / N-router / N-summary | Chat sau |
| N-autotag-chat / N-vision-scan-all / N-open / N-guest-chat | Cấm |
| N-replace-sql-search | Không thay listed/orders |
| Index `incorrect_tags` vào vector | Bỏ (đã đánh giá) |

---

## 7. Files Plan #1

- [base requirement.md](base%20requirement.md)  
- [PLANNING_TRIO.md](PLANNING_TRIO.md)
