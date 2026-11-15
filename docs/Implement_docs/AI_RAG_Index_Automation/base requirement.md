# Base requirement — AI_RAG_Index_Automation

**Input Plan #1 (ngắn).** Chi tiết: [business_requirement.md](business_requirement.md).

## Một câu

Tự động index pin/tag RAG còn thiếu bằng job định kỳ (Beat); CLI fallback; hook realtime = phase sau.

## Phải có

- Scheduled job: missing pins + missing/stale tags  
- Limit + pause / tôn trọng quota  
- Không embed sync trong HTTP  
- CLI `reindex_rag` vẫn chạy  

## Không làm sprint này

Hook create-pin/tag (phase A — chỉ note) · Admin UI backlog · JD · Jina · Vision-OCR  
