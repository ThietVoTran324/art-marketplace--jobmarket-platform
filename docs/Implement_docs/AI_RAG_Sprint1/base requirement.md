# Base requirement — AI_RAG_Sprint1

**Input Plan #1 (ngắn).** Chi tiết: [business_requirement.md](business_requirement.md).

## Một câu

Thêm RAG vào chat: FAQ corpus → chunk → embed (API) → Postgres vector → retrieve + cite; giữ SQL tools marketplace; offline reindex; hướng tới sau: FAQ + pin text.

## Phải có

- Full pipeline gắn chat (tool retrieve)  
- Cite bắt buộc; không bịa khi thiếu context  
- FAQ public only; login-only; API embed; Postgres+vector hướng  
- Không thay listed/search_pins SQL  

## Không làm Sprint1 (RAG)

Pin/JD embed (→ wave 1.1 / sau) · summary memory · LangChain bắt buộc · self-host embed · multimodal · inject feed · retag / vision-all / open ChatGPT  

→ BR §6.
