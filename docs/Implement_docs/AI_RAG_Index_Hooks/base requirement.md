# Base requirement — AI_RAG_Index_Hooks

**Input Plan #1 (ngắn).** Chi tiết: [business_requirement.md](business_requirement.md).

## Một câu

Enqueue Celery 1 pin / 1 tag khi create-update (và sau auto-tag); Beat missing hàng ngày giữ safety net; không embed sync HTTP.

## Phải có

- Hook async pin (create / text-tag đổi / sau auto-tag success)  
- Hook async tag (mới + đổi tên)  
- Flag `AI_RAG_HOOK_ENABLED` opt-in  
- Xóa pin → gỡ RAG async  
- Beat B + CLI vẫn chạy  

## Không làm sprint này

Admin UI reindex pins/tags · JD · Jina · Vision-OCR · tắt Beat · sync embed  
