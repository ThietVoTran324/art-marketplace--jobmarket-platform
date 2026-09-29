# Devplan checklist — Marketplace_Sprint7

**Prerequisite:** Plan #2 CHỐT · head `f8a9b0c1d2e3`  
**CLOSED:** 2026-09-28 · Alembic `a9b0c1d2e3f4` · `scripts/smoke_marketplace_sprint7.py` → `ALL_SMOKE_PASS`

## P1 — Watermark + regenerate

- [x] `apply_watermark`: logo + text band (`PREVIEW · NOT LICENSED`)
- [x] Re-run `generate_pin_preview` via `scripts/regenerate_pin_previews.py` (12 pins ok)

## P2 — List gate

- [x] `assert_pin_media_ready(pin)` — original + image + content_sha256 (+ files on disk)
- [x] Wire create/relist listing routes

## P3 — PinOut strip

- [x] Remove/exclude `original_image` from public PinOut; add `has_original`
- [x] FE PinView Download uses `has_original`

## P4 — Audit

- [x] Migration `a9b0c1d2e3f4` + model `PinOriginalAccessLogsOrm`
- [x] Log on mint + `/file`

## P5 — Close

- [x] Smoke script / manual AC-01…06 (`ALL_SMOKE_PASS`)
- [x] SECURITY_FOLLOWUPS T2-04 done; trio + map CLOSED
