# Base requirement — AI_Chat_Sprint1

**Input Plan #1 (ngắn).** Chi tiết CHỐT: [business_requirement.md](business_requirement.md).

## Một câu

Floating AI chatbox (login): soft-closed về sản phẩm art/marketplace/job; skills tra cứu public + “của tôi”; 1 thread/user trên Postgres; quota; read-only; không gọi auto-tag.

## Phải có

- Widget góc phải dưới, mọi page; guest → login  
- Soft-closed + reject lạc đề  
- Skills + authz phân lớp public/private  
- Postgres history; 1 conversation/user  
- Quota chống burn  
- Tách system auto-tag  

## Không làm Sprint1

Streaming · RAG · LangChain bắt buộc · mutate qua bot · Mongo SSOT chat · multi-thread · 2 model router · open ChatGPT  

→ Ghi note học/làm sau trong BR §5 và learning path.
