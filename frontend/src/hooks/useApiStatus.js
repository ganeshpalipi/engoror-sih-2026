import { useEffect, useState } from 'react'

/**
 * Minimal data-fetching hook for Phase 1 (used by Home; reused by
 * Model Status and other pages in later phases).
 *
 * Returns { data, error, loading }. Errors arrive as human-friendly
 * strings thrown by services/api.js.
 */
export function useApiStatus(fetcher) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    // loading starts as `true`, so no synchronous setState is needed here
    fetcher()
      .then((d) => {
        if (active) {
          setData(d)
          setError('')
        }
      })
      .catch((e) => {
        if (active) setError(e.message || 'Something went wrong')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
    // Intentionally runs once on mount; callers pass a stable module-level
    // fetcher (see services/api.js). Re-fetch logic comes with later phases.
  }, [])

  return { data, error, loading }
}
