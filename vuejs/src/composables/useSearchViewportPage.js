/**
 * Search result windowing: estimate how many pin cards fill one viewport
 * (matches PinsBySearch grid: cols-2 / sm:3 / md:4 / lg:5, aspect-[3/4]).
 */

export function estimateSearchPageSize(
  {
    innerWidth = typeof window !== 'undefined' ? window.innerWidth : 1024,
    innerHeight = typeof window !== 'undefined' ? window.innerHeight : 800,
  } = {},
  pinCountHint = null,
) {
  if (pinCountHint != null) {
    const n = Number(pinCountHint)
    if (Number.isFinite(n) && n >= 1) {
      return Math.min(100, Math.max(1, Math.floor(n)))
    }
  }

  let cols = 2
  if (innerWidth >= 1024) cols = 5
  else if (innerWidth >= 768) cols = 4
  else if (innerWidth >= 640) cols = 3

  // Home search grid: ml-20 + mr-6 + gaps ≈ 120px chrome
  const colW = Math.max(100, (innerWidth - 120) / cols)
  // aspect-[3/4] → height = width * 4/3; + padding
  const cardH = colW * (4 / 3) + 16
  // nav + tag strip + mt ≈ 160px
  const usableH = Math.max(280, innerHeight - 160)
  const rows = Math.max(1, Math.ceil(usableH / cardH))
  // One viewport only; clamp so we never blast dozens of uploads on Enter
  return Math.min(20, Math.max(cols, cols * rows))
}

export function nextSearchPageSize(firstPageSize) {
  const n = Math.max(1, Number(firstPageSize) || 10)
  return Math.min(10, Math.max(5, Math.ceil(n / 2)))
}
