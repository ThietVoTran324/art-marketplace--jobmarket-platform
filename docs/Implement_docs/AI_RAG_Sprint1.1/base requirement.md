# Base requirement — AI_RAG_Sprint1.1 (Plan A)

**Chi tiết:** [business_requirement.md](business_requirement.md).

## Một câu

Mở rộng RAG: pin title/desc/tags + parent–child + hybrid RRF; thêm Intent→English tags→khớp catalog (read-only); không retag / không Vision-OCR.

## Phải có

- Pin-text index public + semantic/parent-child  
- Hybrid vector + keyword + RRF  
- Intent structured tags (1–4, English kebab-case) → embed-match catalog → SQL/rank  
- Cite pin url/thumb; SQL marketplace giữ; FAQ Sprint1 không regress  

## Không làm

Vision-OCR · FAQ CMS · index incorrect_tags · chatbot retag · thay SQL listed/orders · Jina/JD bắt buộc  
