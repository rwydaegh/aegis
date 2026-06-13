import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchPhantom } from './api'
import { useStudioStore } from './store'

// The store does not carry a phantom-mesh selector yet, so the studio renders the
// canonical thelonious phantom (the mesh the e11 geometry is baked around, and the
// only phantom the manifest advertises).
const MESH = 'thelonious'

// Fetch the phantom geometry and store it. Race-safe via a monotonic request id
// (the same pattern as useStudioRays): under React 18 StrictMode the effect runs,
// is torn down, and runs again on mount. A "fetch once" ref guard would let the
// first (now stale) request win the guard while its result is discarded, leaving
// the store empty; the id check instead lets the live mount's fetch commit.
export function useStudioPhantom(): void {
  const latestRef = useRef(0)

  useEffect(() => {
    const myId = ++latestRef.current
    const isStale = () => myId !== latestRef.current

    fetchPhantom(MESH)
      .then((geom) => {
        if (isStale()) return
        useStudioStore.getState().setPhantom(geom)
      })
      .catch((err) => {
        if (isStale()) return
        Sentry.captureException(err)
      })
  }, [])
}
