# Base requirement — AI_RAG_FAQ_CMS

**Input Plan #1 (ngắn).** Chi tiết: [business_requirement.md](business_requirement.md).

## Một câu

Admin soạn FAQ trên CMS (DB) → publish → reindex → chat RAG cite; thay dần seed markdown git.

## Phải có

- DB = SSOT FAQ cho RAG; md chỉ seed/import một lần  
- Draft / Published; chỉ published vào index  
- Admin-only CRUD + reindex FAQ (bài / all FAQ)  
- Cite + login-only; không regress chat / Plan A  

## Không làm sprint này

Trang `/help` public · reindex pins/tags UI · JD embed · Jina bắt buộc · Vision-OCR · i18n bắt buộc 2 ngôn ngữ  
