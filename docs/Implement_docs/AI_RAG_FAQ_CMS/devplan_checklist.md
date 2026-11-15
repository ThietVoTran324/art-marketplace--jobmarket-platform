# Devplan checklist — AI_RAG_FAQ_CMS

**Plan #2 CHỐT:** [plan_mode_decisions.md](plan_mode_decisions.md)

## A. Data

- [x] Migration `faq_articles`
- [x] ORM `FaqArticlesOrm`
- [x] Seed script từ corpus md

## B. Reindex

- [x] Reindex FAQ từ CMS (published)
- [x] Unpublish → xóa doc/chunks
- [x] Celery reindex one + all FAQ
- [x] CLI `reindex_rag --faq` dùng CMS khi có published

## C. Admin API + UI

- [x] REST `/admin/faq*`
- [x] Vue `/admin/faq` + AdminNav + i18n

## D. Prove

- [ ] Seed → list admin
- [ ] Draft không vào chat; publish → cite
- [ ] Unpublish → hết cite
- [ ] Chat / Plan A không regress

## Out

`/help` · pins/tags reindex UI · JD · Jina · Vision-OCR  
