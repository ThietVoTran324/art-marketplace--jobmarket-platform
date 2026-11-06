/**
 * Preview URLs for feed cards — always via /api/pins/upload/{id} (watermark gate).
 * Browser HTTP cache (Cache-Control on API) replaces former axios→blob downloads.
 */

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

/** @deprecated Prefer pinPreviewUrl — kept for call sites expecting async. */
export async function fetchPinMediaUrl(pinId, imageId = null) {
  return pinPreviewUrl(pinId, imageId)
}
