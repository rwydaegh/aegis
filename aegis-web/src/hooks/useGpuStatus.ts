import { useEffect, useRef } from 'react'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { fetchGpuStatus } from '@/api/client'

const POLL_INTERVAL = 30_000  // 30 seconds

/**
 * Polls /api/gpu/status when ray tracing is enabled.
 * Updates gpuWarm in the UI store.
 */
export function useGpuStatus() {
  const rtEnabled = useSceneStore(s => s.pathSource === 'rt')
  const setGpuWarm = useUIStore(s => s.setGpuWarm)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!rtEnabled) {
      setGpuWarm(null)
      return
    }

    const poll = () => {
      fetchGpuStatus()
        .then(status => setGpuWarm(status.enabled ? status.warm : null))
        .catch(() => setGpuWarm(null))
    }

    // Poll immediately, then every 30s
    poll()
    intervalRef.current = setInterval(poll, POLL_INTERVAL)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [rtEnabled, setGpuWarm])
}
