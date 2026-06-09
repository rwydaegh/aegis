import { useEffect, useState } from 'react'
import { fetchGpuStatus, type GpuStatus } from '@/api/client'

// Poll the shared Modal GPU status endpoint so the lab can show whether the
// ray-tracing GPU is warm. Lab-local (not the main useUIStore) so the lab stays
// self-contained, but it hits the same /api/gpu/status the main viewer polls.
const POLL_INTERVAL = 30_000

export function useLabGpuStatus(): GpuStatus | null {
  const [status, setStatus] = useState<GpuStatus | null>(null)

  useEffect(() => {
    let cancelled = false
    const poll = () => {
      fetchGpuStatus()
        .then((s) => {
          if (!cancelled) setStatus(s)
        })
        .catch(() => {
          if (!cancelled) setStatus(null)
        })
    }
    poll()
    const id = setInterval(poll, POLL_INTERVAL)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  return status
}
