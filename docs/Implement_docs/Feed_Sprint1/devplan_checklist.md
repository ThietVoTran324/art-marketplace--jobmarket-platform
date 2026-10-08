# Devplan checklist — Feed_Sprint1

**Plan #2 CHỐT** 2026-10-08. Prove-done theo AC BR.

## P0 — Config + ranker + route

- [x] `INTERACTION_WEIGHTS` + pool ratios + diversity constants (`feed_config.py`)
- [x] Ranker: pools Following / Affinity / Explore / Trending / Fresh → dedupe → score → diversity (`feed_ranker.py`)
- [x] `GET /api/pins/?mode=home|chrono` (default home); chrono = `order by id desc` cũ
- [x] Guest home lite; login full blend; cold-start fallback + exception → chrono
- [x] Exclude/demote view+save 7d (Q5)

## P1 — Wire affinity + FE

- [x] Affinity từ tags of liked/saved/viewed pins + weights
- [x] HomeView: default `mode=home`; `?mode=chrono` opt-out timeline
- [x] Aside recommend giữ nguyên (không đụng)

## P2–P3 — Diversity + weights

- [x] Author streak ≤2; tag streak ≤3
- [x] Fresh + trending (~7d) trong pools
- [x] Weights tập trung `INTERACTION_WEIGHTS`

## Prove-done

- [ ] Two users different affinity → observable home order diff (AC-02)
- [ ] `mode=chrono` = legacy timeline
- [ ] Guest home 200; no 500 on empty signals
- [ ] Tag browse / search unchanged
