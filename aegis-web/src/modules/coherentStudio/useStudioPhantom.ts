import { useEffect, useRef } from 'react'
import * as Sentry from '@sentry/react'
import { fetchPhantom } from './api'
import { useStudioStore } from './store'

// Fetch the phantom geometry and store it whenever the selected mesh changes.
// Race-safe via a monotonic request id (the same pattern as useStudioRays):
// under React 18 StrictMode the effect runs, is torn down, and runs again on
// mount. A "fetch once" ref guard would let the first (now stale) request win
// the guard while its result is discarded, leaving the store empty; the id
// check instead lets the live mount's fetch commit. Re-fetching on mesh change
// also clears the stale body so the new phantom's geometry replaces it.
export function useStudioPhantom(): void {
  const mesh = useStudioStore((s) => s.mesh)
  // The UE slider moves the body down the corridor: each position ships its own
  // translated phantom pack, so refetch the geometry when it changes too.
  const ueIdx = useStudioStore((s) => s.ueIdx)
  const latestRef = useRef(0)

  useEffect(() => {
    const myId = ++latestRef.current
    const isStale = () => myId !== latestRef.current

    fetchPhantom(mesh, ueIdx)
      .then((geom) => {
        if (isStale()) return
        useStudioStore.getState().setPhantom(geom)
      })
      .catch((err) => {
        if (isStale()) return
        Sentry.captureException(err)
      })
  }, [mesh, ueIdx])
}
