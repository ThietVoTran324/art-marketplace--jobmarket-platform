import axios from 'axios';

const cache = new Map();
const inflight = new Map();

export function getCachedCompanyAvatar(ownerUserId) {
  if (!ownerUserId) return null;
  return cache.get(Number(ownerUserId)) || null;
}

export async function fetchCompanyAvatar(ownerUserId) {
  const id = Number(ownerUserId);
  if (!Number.isFinite(id) || id <= 0) return null;
  if (cache.has(id)) return cache.get(id);
  if (inflight.has(id)) return inflight.get(id);

  const p = axios
    .get(`/api/users/upload/${id}`, { responseType: 'blob' })
    .then((r) => {
      const url = URL.createObjectURL(r.data);
      cache.set(id, url);
      inflight.delete(id);
      return url;
    })
    .catch(() => {
      inflight.delete(id);
      return null;
    });
  inflight.set(id, p);
  return p;
}

export async function prefetchCompanyAvatars(ownerUserIds) {
  const ids = [...new Set((ownerUserIds || []).map(Number).filter((n) => n > 0))];
  await Promise.all(ids.map((id) => fetchCompanyAvatar(id)));
}
