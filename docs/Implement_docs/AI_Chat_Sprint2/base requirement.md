# Base requirement — AI_Chat_Sprint2

**Input Plan #1 (ngắn).** Chi tiết CHỐT: [business_requirement.md](business_requirement.md).

## Một câu

Nâng chat MVP: discovery listed-pins + cite path/markdown + search qua tag/index (không vision-all) + SSE + clear history; soft-closed nới tư vấn art; vẫn login-only, 1 thread, read-only, cấm chatbot retag.

## Phải có (wave 2.A + 2.B)

- Matrix public vs private rõ trong BR  
- Listed-pins skill + cite `path` + FE markdown clickable  
- Search title/desc/tag; cấm vision-scan catalog  
- SSE streaming (degrade rõ nếu cần)  
- Clear 1 conversation/user  
- Soft-closed nới art; không open ChatGPT  

## Không làm Sprint2 (note rõ → BR §6)

LangChain/LangGraph · router 2-model · RAG/embed · summary memory · vision rerank ≤N · mutate · Mongo ctx · multi-thread · xóa từng msg · WS · guest chat · **chat retag** · **vision-scan-all** · open ChatGPT  

→ Chi tiết ID `N-*` trong [business_requirement.md](business_requirement.md) §6.
