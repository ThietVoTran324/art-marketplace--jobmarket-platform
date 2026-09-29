/**
 * Canonical profile deep links for tabs / nested views.
 * Example: /user/alice?tab=experience&workExpId=12
 *          /user/alice?tab=saved&boardId=3
 */
export const PROFILE_TABS = Object.freeze([
  'created',
  'saved',
  'liked',
  'experience',
  'credentials',
  'cv',
  'company',
  'hiring',
  'manage-jobs',
  'employees',
])

export function profilePath(username, { tab, workExpId, boardId } = {}) {
  const u = encodeURIComponent(String(username || '').trim())
  const q = new URLSearchParams()
  if (tab && PROFILE_TABS.includes(tab)) q.set('tab', tab)
  if (workExpId != null && workExpId !== '') q.set('workExpId', String(workExpId))
  if (boardId != null && boardId !== '') q.set('boardId', String(boardId))
  const qs = q.toString()
  return qs ? `/user/${u}?${qs}` : `/user/${u}`
}
