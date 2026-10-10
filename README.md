# Art Marketplace + Job Market Platform

Full-stack Pinterest-inspired image sharing platform — FastAPI + Vue 3 — extended with **roles & audit**, a **Job Market**, a **pin-license Marketplace** (SePay), and an **Admin Ops** console.

**Repo:** [ThietVoTran324/art-marketplace--jobmarket-platform](https://github.com/ThietVoTran324/art-marketplace--jobmarket-platform)

Built to practice production-shaped backend patterns: REST, GraphQL, realtime, Celery, multi-store data, CSRF/session cookies, and sprint-based delivery.

---

## Product review

Soft-live demo surfaces (discover → buy → hire → chat):

1. **Home / tag filter** — masonry feed with horizontal tag chips for niche browsing  
2. **Home feed (guest)** — unauthenticated grid; ranking favors likes → views → comments → saves  
3. **Pin detail** — engagement stats, Save, tags, “More like this”  
4. **Marketplace listing / watermark** — for-sale price + diagonal watermark until purchase  
5. **Checkout** — SePay bank transfer (amount, memo, QR, payment polling)  
6. **Artist profile** — Created / Saved / Liked plus Experience & Credentials  
7. **Company page** — Overview / Opening jobs / Reviews, roster  
8. **Explore jobs** — search, filters, suggest list, split detail pane  
9. **Job detail + Apply** — salary, locations, requirements, application status  
10. **Messages** — WebSocket chat, accent color, shared media  

---

## What shipped (product domains)

| Domain | Status | Highlights |
|--------|--------|------------|
| **Core social** | Live | Pins, boards, likes, comments, search, profiles, follows, chat (WebSocket), notifications (SSE), recommendations, personalized + guest-popularity home feed |
| **Phase 0 — trust** | CLOSED | Roles (`admin` / `artist` / `employer` / `seller`), ownership checks, append-only audit log |
| **Job Market** | CLOSED | Company KYC / hiring rights, credentials, job posts, applications + CV, work-experience approval, company public page, JD reports & suspend |
| **Marketplace** | CLOSED | Seller eligibility, watermarked preview / signed original ACL, listings, SePay orders, copyright reports + license certificates |
| **Admin Ops** | CLOSED (MVP) | `/admin`: roles, audit, moderation, KYC, credentials, job reports, copyright, work-exp queues |

---

## Features

### Social / media
- Masonry feed, tag chips, search  
- Comments, likes, profiles, followers  
- Realtime chat (WebSocket) and updates (SSE)  
- JWT cookie auth + Google OAuth2; CSRF on mutating requests  
- Guest home ranked by engagement; logged-in affinity personalization  

### Job Market
- Employer company verification (KYC)  
- Artist credentials, CVs, job explore / apply  
- Company brand page (Overview / jobs / reviews)  
- Work experience linked to companies (approve flow)  
- Job post reporting and company suspend / unsuspend  

### Marketplace
- One-shot personal-use licenses per pin  
- Watermarked preview; original via signed URL + ACL  
- SePay webhook (+ local mock when `DEV_MODE` + `MP_SEPAY_MOCK`)  
- Copyright reports; resolve unlists listing (MVP)  

### Admin (`/admin`, role `admin`)
- Overview, roles, audit, pin/comment moderation  
- KYC / credentials / job reports / copyright / work-exp queues  

---

## Architecture

```
Client (Vue 3)
│
├── REST  /api/*
├── GraphQL
│
▼
FastAPI
│
├── Auth (JWT cookies + CSRF + Google OAuth)
├── Roles / ownership / audit
├── Job Market + Marketplace routers
│
├── PostgreSQL (primary + Alembic)
├── Redis (cache, revoke, limiter)
├── Celery + Beat (preview/hash, mail, order TTL, …)
└── Realtime: WebSockets + SSE
```

Lean live stack also keeps MongoDB + RabbitMQ for boot/demos; product SSOT remains PostgreSQL.

---

## Tech stack

**Backend:** FastAPI, SQLAlchemy (async), Alembic, Strawberry GraphQL, Celery, Redis, RabbitMQ, JWT + OAuth2  

**Data:** PostgreSQL (main), Redis (+ MongoDB in compose for legacy demos)  

**Frontend:** Vue 3, Pinia, Vue Router, Tailwind CSS, Axios, vue-i18n (EN/VI)  

**Ops:** Docker Compose (`docker-compose.prod.yml` lean live), Nginx  

---

## Project layout

```
.
├── app/                 # FastAPI (REST, GraphQL, Celery, migrations, models)
├── vuejs/               # Vue 3 client (admin/, JobMarket/, …)
├── docker-compose.yml
├── docker-compose.dev.yml
└── docker-compose.prod.yml
```

---

## Quick start (Docker)

**Local (full + HMR):**

```bash
docker network create pinterest-network   # once
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API / health | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |

**Live / lean demo** (FE on `:80` via Nginx; DB ports not published):

```bash
docker network create pinterest-network   # once
docker compose -f docker-compose.prod.yml up -d --build
```

| Service | URL |
|---------|-----|
| Frontend + API (proxied) | http://localhost/ |
| Health | http://localhost/api/health |

---

## Async processing

```
API request → Redis/RabbitMQ broker → Celery worker → DB / mail / media
```

---

## Credits

Frontend UI adapted from: https://github.com/kingyiusuen/pinterest-clone

---

## License

MIT License — free to use and modify.
