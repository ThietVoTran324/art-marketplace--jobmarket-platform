# Feed Search Wave1 — security follow-ups

> Enter-only search + media cache + embedded meta (2026-11-06).  
> Index SSOT: [`../../Planing_docs/security_followups_type1_type2.md`](../../Planing_docs/security_followups_type1_type2.md) · backlog §G.

## Type 1 — FIXED (2026-11-06)

| ID | Fix |
|----|-----|
| T1-09 | `clearFeedMetaCache()` on logout |
| T1-10 | Drop `immutable` on `/pins/upload/{id}`; `max-age=3600` |
| T1-11 | Search + feed-meta: `Cache-Control: private, no-store` |

## Type 2 — DEFER (next media / feed-search sprint)

| ID | Issue | Pull when |
|----|-------|-----------|
| T2-SEARCH-01 / SEC-T2-SEARCH-01 | Public preview hotlink (by design) | CDN / Referer policy product choice |
| T2-SEARCH-02 / SEC-T2-SEARCH-02 | Resolve Redis stale ≤~60s if invalidate miss | Tag-admin audit / ops |
| T2-SEARCH-03 / SEC-T2-SEARCH-03 | `?v=content_hash` cache-bust on re-preview | Media hardening |

Do **not** implement Type 2 in the same ship as T1-09…11 unless product CHỐT pulls an ID up.
