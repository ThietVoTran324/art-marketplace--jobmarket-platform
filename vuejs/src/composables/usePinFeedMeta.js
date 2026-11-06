/**
 * Shared feed-card meta cache + batch prefetch.
 * Keys: pin_id → { username, likes_count, liked, comments_count }
 */
import axios from 'axios'

const metaByPinId = new Map()
let inflightIds = null

export function getCachedFeedMeta(pinId) {
  const id = Number(pinId)
  if (!Number.isFinite(id) || id <= 0) return null
  return metaByPinId.get(id) ?? null
}

export function patchFeedMeta(pinId, patch) {
  const id = Number(pinId)
  if (!Number.isFinite(id) || id <= 0) return
  const prev = metaByPinId.get(id) || {
    pin_id: id,
    username: null,
    likes_count: 0,
    liked: false,
    comments_count: 0,
  }
  metaByPinId.set(id, { ...prev, ...patch, pin_id: id })
}

/** Seed cache from search (or other) payloads that already embed feed-meta fields. */
export function seedFeedMetaFromPins(pins) {
  for (const pin of pins || []) {
    const id = Number(pin?.id)
    if (!Number.isFinite(id) || id <= 0) continue
    if (
      pin.username == null &&
      pin.likes_count == null &&
      pin.liked == null &&
      pin.comments_count == null
    ) {
      continue
    }
    patchFeedMeta(id, {
      username: pin.username ?? null,
      likes_count: Number(pin.likes_count) || 0,
      liked: !!pin.liked,
      comments_count: Number(pin.comments_count) || 0,
    })
  }
}

/** Prefetch meta for a page of pins (skips ids already cached). */
export async function prefetchFeedMeta(pinIds) {
  const ids = [...new Set((pinIds || []).map(Number).filter((n) => Number.isFinite(n) && n > 0))]
  const missing = ids.filter((id) => !metaByPinId.has(id))
  if (!missing.length) return

  // Coalesce concurrent prefetches that overlap
  const body = { pin_ids: missing }
  const request = axios.post('/api/pins/feed-meta', body).then(({ data }) => {
    for (const row of data || []) {
      metaByPinId.set(row.pin_id, {
        pin_id: row.pin_id,
        username: row.username ?? null,
        likes_count: Number(row.likes_count) || 0,
        liked: !!row.liked,
        comments_count: Number(row.comments_count) || 0,
      })
    }
    return data
  })

  inflightIds = request
  try {
    await request
  } finally {
    if (inflightIds === request) inflightIds = null
  }
}
