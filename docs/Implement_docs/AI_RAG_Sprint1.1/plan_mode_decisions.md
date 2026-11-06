# Plan #2 decisions — AI_RAG_Sprint1.1 (Plan A)

**CHỐT** 2026-11-06 — **all suggest** technical.  
**Rule Intent:** user mọi ngôn ngữ → `predicted_tags` **chỉ English kebab-case** (khớp catalog / auto-tag).

BR: [business_requirement.md](business_requirement.md) · Trio: [PLANNING_TRIO.md](PLANNING_TRIO.md)

---

## 1. Quiz → CHỐT

| ID | CHỐT | Ghi chú |
|----|------|---------|
| T1 | **A** Skill `predict_search_tags` → embed-match catalog → `matched_tags` (+ optional pin hints) | Không retag / không ghi DB tags |
| T2 | **A** Cache/bảng embed mọi `tags.name`; job reindex khi tag mới | |
| T3 | **A** `source_type=pin`; parent = pin; children chunks + parent pin id | |
| T4 | **A** Hybrid vector + keyword → RRF; có thể fuse thêm nhánh matched_tags | |
| T5 | **A** Gemini Flash-Lite (+ JSON schema) cho intent | Prompt: any language → English tags |
| T6 | **A** Config ngưỡng match + caps (predicted ≤4, matched ≤8) | |
| T7 | **A** Script `reindex_rag --pins` batch + hash skip | |
| T8 | **A** Out BR §6 | |

---

## 2. Intent → tags (tech sketch)

### Skill `predict_search_tags`
- Input: user query text (mọi ngôn ngữ).  
- Model: structured JSON  
  `{ "reasoning": "...", "predicted_tags": ["kebab-case", ...] }`  
- **Contract:** `predicted_tags` **English only**, 0–4 items; `[]` nếu không suy ra được.  
- Backend: `normalize_tag_name` từng predicted → embed → cosine vs **tag catalog embeddings** → lọc `score >= AI_RAG_TAG_MATCH_MIN_SCORE` → `matched_tags` (tên DB thật).  
- **Cấm:** insert/update `pins_tags` / gọi `analyze_pin_image` / Celery retag.

### Prompt intent (bắt buộc có)
- System tags trên platform là English kebab-case.  
- Dù user VI / EN / slang / trộn ngôn ngữ → map sang English tags.  
- Ví dụ: `"ảnh chill buổi sáng"` → `["serene","morning","soft-light"]` (không `bình_yên`).

### Tag catalog embed
- Offline job: embed tất cả `TagsOrm.name` (hoặc distinct đang dùng).  
- Query path chỉ embed 1–4 predicted (rẻ).

---

## 3. Pin RAG schema sketch

### Documents
- `source_type='pin'`, `source_key=str(pin_id)`, title, path=`/pin/{id}`, content_hash  
- body optional = ghép title+desc+tags để hash  

### Chunks (parent–child)
- Parent logical = document pin  
- Children: `chunk_kind` ∈ title | description | tags | semantic_slice  
- `embedding` vector; meta JSONB `{ "pin_id", "chunk_kind" }`  

FAQ documents Sprint1 giữ nguyên `source_type=faq`.

---

## 4. Hybrid + RRF

Nhánh (có thể config bật/tắt):
1. **Vector** trên pin children  
2. **Keyword** title/desc/tag (ILIKE/FTS)  
3. Optional **matched_tags** filter/boost từ intent skill  

Fuse bằng **RRF**; top-k sau fuse; cite **parent pin** (url + thumb).

`retrieve_knowledge` mở rộng: FAQ + pin (hoặc skill pin riêng gọi chung retrieve service) — chi tiết implement checklist.

---

## 5. API / ops

| Việc | Hướng |
|------|--------|
| Chat tools | + `predict_search_tags`; retrieve dùng matched_tags khi có |
| Reindex pins | `python -m scripts.reindex_rag --pins` (± `--from-id`/`--to-id`) |
| Reindex tag embeds | cùng script flag `--tags` hoặc bước trong reindex |
| Celery | optional task reindex pin/tags (không block chat) |

---

## 6. Config keys

| Key | Default gợi ý |
|-----|----------------|
| `AI_RAG_INTENT_TAGS_ENABLED` | true khi ship 1.1 |
| `AI_RAG_TAG_MATCH_MIN_SCORE` | 0.55–0.7 (tune) |
| `AI_RAG_PREDICTED_TAGS_MAX` | 4 |
| `AI_RAG_MATCHED_TAGS_MAX` | 8 |
| `AI_RAG_RRF_K` | 60 |
| Giữ `AI_RAG_*` Sprint1 | embed provider/model/dims/top_k |

---

## 7. Out (không sót)

Vision-OCR · FAQ CMS · Jina bắt buộc · JD · index incorrect_tags · chatbot retag · thay SQL listed/orders · LangChain bắt buộc · summary memory · vision-scan-all · open/guest full chat  

---

## 8. Files chạm (implement sau lệnh)

- `app/ai/rag/` chunk parent-child, hybrid RRF, intent tags, tag catalog embed  
- Migration nếu cần cột `chunk_kind` / bảng tag_embeddings  
- Skills + prompts chat  
- `scripts/reindex_rag.py` flags `--pins` / `--tags`  
- Config / `.env.example`  
