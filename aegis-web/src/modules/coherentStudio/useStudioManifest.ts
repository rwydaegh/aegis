import { useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { fetchManifest } from './api'
import { useStudioStore } from './store'
import type { StudioUeAntenna } from './store'
import type { StudioFocusMode, Vec3 } from './api'

function isVec3(v: unknown): v is Vec3 {
  return Array.isArray(v) && v.length === 3 && v.every((n) => typeof n === 'number')
}

// On mount: fetch the manifest, store it, and seed the store params from the
// backend default_scene (snake_case -> the store's camelCase fields). Seeding the
// params is what kicks off the first slice / body-map fetches via their hooks.
export function useStudioManifest(): void {
  useEffect(() => {
    let cancelled = false
    fetchManifest()
      .then((m) => {
        if (cancelled) return
        const s = useStudioStore.getState()
        s.setManifest(m)

        const d = (m.default_scene ?? {}) as Record<string, unknown>
        if (typeof d.condition === 'string') s.setCondition(d.condition)
        if (typeof d.array_n === 'number') s.setArrayN(d.array_n)
        if (typeof d.seed === 'number') s.setSeed(d.seed)
        if (d.ue === 'dipole') s.setUeAntenna(d.ue as StudioUeAntenna)
        if (typeof d.beam === 'string') s.setBeam(d.beam)
        if (d.focus_mode === 'at-skin' || d.focus_mode === 'free-space') {
          s.setFocusMode(d.focus_mode as StudioFocusMode)
        }
        if (isVec3(d.focus_xyz)) s.setFocusXyz(d.focus_xyz)
        if (typeof d.frequency_ghz === 'number') s.setFrequencyGhz(d.frequency_ghz)
      })
      .catch((err) => {
        if (cancelled) return
        Sentry.captureException(err)
      })
    return () => {
      cancelled = true
    }
  }, [])
}
