/** Small formatting helpers shared across pages. */

// 823 -> "823 ms" ; 2450 -> "2.45 s" ; null -> "—"
export function formatMs(ms) {
  if (ms == null || Number.isNaN(ms)) return '—'
  if (ms < 1000) return `${Math.round(ms)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

// "ok" -> green class names, "error" -> red, anything else -> neutral
export function statusClass(status) {
  if (status === 'ok') return 'ok'
  if (status === 'error' || status === 'degraded') return 'err'
  return 'wait'
}
