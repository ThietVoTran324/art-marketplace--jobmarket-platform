/**
 * Preview URLs for feed cards — always via /api/pins/upload/{id} (watermark gate).
 * Browser HTTP cache (Cache-Control on API) replaces former axios→blob downloads.
 * Does not change encode quality / detail PinView (same preview endpoint).
 */

const prefetchStarted = new Set()

export function pinPreviewUrl(pinId, imageId = null) {
  const id = Number(pinId)
  if (!Number.isFinite(id) || id <= 0) return null
  const base = `/api/pins/upload/${id}`
  if (imageId != null && Number(imageId) > 0) {
    return `${base}?image_id=${Number(imageId)}`
  }
  return base
}

export function getCachedPinMediaUrl(pinId) {
  return pinPreviewUrl(pinId)
}

/** Warm browser HTTP cache for above-fold search/feed cards (deduped). */
export function prefetchPinPreviewUrls(pinIds, { limit = 12 } = {}) {
  if (typeof Image === 'undefined') return
  const ids = [...new Set((pinIds || []).map(Number).filter((n) => Number.isFinite(n) && n > 0))]
  const cap = Math.max(1, Math.min(30, Number(limit) || 12))
  for (const id of ids.slice(0, cap)) {
    const url = pinPreviewUrl(id)
    if (!url || prefetchStarted.has(url)) continue
    prefetchStarted.add(url)
    const img = new Image()
    img.decoding = 'async'
    img.src = url
  }
}

/** @deprecated Prefer pinPreviewUrl — kept for call sites expecting async. */
export async function fetchPinMediaUrl(pinId, imageId = null) {
  return pinPreviewUrl(pinId, imageId)
}
