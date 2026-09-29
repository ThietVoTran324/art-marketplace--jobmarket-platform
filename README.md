# Pinterest-like Image Marketplace

Full-stack Pinterest-inspired image sharing platform — FastAPI + Vue 3 — extended with **roles & audit**, a **Job Market**, a **pin-license Marketplace** (SePay), and an **Admin Ops** console.

Built to practice production-shaped backend patterns: REST, GraphQL, realtime, Celery, multi-store data, CSRF/session cookies, and sprint-based delivery with smoke scripts.

---

## What shipped (product domains)

| Domain | Status | Highlights |
|--------|--------|------------|
| **Core social** | Live | Pins, boards, likes, comments, search, profiles, follows, chat (WebSocket), notifications (SSE), recommendations |
| **Phase 0 — trust** | CLOSED | User roles (`admin` / `artist` / `employer` / `seller`), ownership checks, append-only audit log |
| **Job Market** | CLOSED | Company KYC / hiring rights, credentials, job posts, applications + CV, work-experience approval, JD reports & company suspend |
| **Marketplace** | CLOSED | Seller eligibility gate, watermarked preview / signed original ACL, listings, payout methods, SePay orders, copyright reports + license certificates |
| **Admin Ops** | CLOSED (MVP) | Vue `/admin` shell: roles, audit, content moderation, KYC queue, credentials override, job reports, copyright (resolve → unlist), work-exp queue |

Planning & sprint history: [`docs/Planing_docs/`](docs/Planing_docs/) · implement trio folders under [`docs/Implement_docs/`](docs/Implement_docs/).

Current Alembic head (Marketplace Sprint5): **`b4c5d6e7f8a9`**.

---

## Features

### Social / media
- Masonry feed, search by tags/keywords, boards & pins  
- Comments, likes, profiles, followers  
- Realtime chat (WebSocket) and updates (SSE)  
- JWT cookie auth + Google OAuth2; CSRF on mutating requests  

### Job Market
- Employer company verification (KYC docs, admin decide)  
- Artist credentials, CVs, job explore / apply  
- Work experience linked to companies (owner + admin approve)  
- Job post reporting and company suspend / unsuspend  

### Marketplace
- Sell **one-shot personal-use** licenses per pin  
- Static watermark preview; original download via signed URL + ACL  
- Seller payment methods; platform commission config  
- SePay webhook (+ local mock when `DEV_MODE` + `MP_SEPAY_MOCK`)  
- Copyright reports; resolve unlists listing (does not revoke paid access in MVP)  

### Admin (`/admin`, role `admin`)
- Overview counts, roles, audit viewer, pin/comment delete  
- KYC / credentials / job reports / copyright / work-exp queues  

---

## Architecture

```
Client (Vue 3 :3000)
│
├── REST  /api/*
├── GraphQL
│
▼
FastAPI (:8000)
│
├── Auth (JWT cookies + CSRF + Google OAuth)
├── Roles / ownership / audit
├── Job Market + Marketplace routers
│
├── PostgreSQL (primary app data + Alembic)
├── MySQL / MongoDB (secondary demos)
├── Redis (cache, revoke, limiter, streams)
├── Celery + Beat (preview/hash, mail, order TTL, …)
├── RabbitMQ (broker / pub-sub demos)
└── Realtime: WebSockets + SSE
```

---

## Tech stack

**Backend:** FastAPI, SQLAlchemy (async), Alembic, Strawberry GraphQL, Celery, Redis, RabbitMQ, JWT + OAuth2  

**Data:** PostgreSQL (main), MySQL, MongoDB, Redis  

**Frontend:** Vue 3, Pinia, Vue Router, Tailwind CSS, Axios  

**Ops:** Docker Compose, Nginx (local), smoke scripts under `scripts/`

---

## Project layout

```
.
├── app/                    # FastAPI application
│   ├── api/rest/           # REST (incl. job_market/, marketplace/, admin/)
│   ├── api/graphql/
│   ├── celery/
│   ├── migrations/         # Alembic
│   ├── postgresql/         # Primary models
│   └── main.py
├── vuejs/                  # Vue 3 app (views/admin/*, JobMarket/*, …)
├── scripts/                # grant_admin, smoke_*, seed helpers
├── docs/
│   ├── Planing_docs/       # Phase / system BR & sprint maps
│   └── Implement_docs/     # Per-sprint planning trio
├── docker-compose.yml
├── docker-compose.dev.yml   # Live reload overlay (local)
└── docker-compose.prod.yml  # Lean live/demo stack (no lab UIs / MySQL)
```

---

## Quick start (Docker)

**Local (full + HMR):**

```bash
docker network create pinterest-network   # once
cp .env.example .env                      # fill secrets; see Marketplace / SePay notes
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API / health | http://localhost:8000/health |
| Swagger | http://localhost:8000/docs |
| Mailhog | http://localhost:8025 |
| PgAdmin | http://localhost:5050 |

**Live / lean demo** (core services only; DB ports not published; FE on `:80` via Nginx):

```bash
docker network create pinterest-network   # once
docker compose -f docker-compose.prod.yml up -d --build
```

| Service | URL |
|---------|-----|
| Frontend + API (proxied) | http://localhost/ |
| Health (via proxy) | http://localhost/api/health |

Optional stacks (PLG, ELK, exporters, services-monitoring) stay in repo but are not part of local-dev or lean-live commands.

Migrations run with the app image / entrypoint as configured in Compose. After code pulls, restart `fastapi-container` if reload did not pick up changes.

### Grant admin (local)

```bash
docker exec -w /fastapi -e PYTHONPATH=/fastapi fastapi-container \
  python scripts/grant_admin.py <username>
```

Then log out / in so the Vue store reloads roles. Open http://localhost:3000/admin (shield icon in the aside).

### Smoke tests (examples)

```bash
docker exec -w /fastapi -e PYTHONPATH=/fastapi fastapi-container \
  python scripts/smoke_admin_sprint4.py
```

Other smokes: `scripts/smoke_phase0_*.py`, `smoke_jobmarket_*.py`, `smoke_marketplace_*.py`, `smoke_admin_sprint1–3.py`. Marketplace SePay smoke needs `DEV_MODE=true` and `MP_SEPAY_MOCK=true`.

---

## Async processing

Celery handles non-blocking work such as pin preview / content hash, email, and marketplace order TTL cancellation:

```
API request → Redis/RabbitMQ broker → Celery worker → DB / mail / media
```

---

## Credits

Frontend UI adapted from: https://github.com/kingyiusuen/pinterest-clone (open-source license of that template).

---

## License

MIT License — free to use and modify.
