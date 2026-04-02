import { useCallback, useRef } from 'react'
import { useOptimizeStore, type OptimizeConstraints } from '@/stores/optimize'
import { useSimulationStore } from '@/stores/simulation'
import { useNotificationStore } from '@/stores/notifications'
import { toServer } from '@/api/coordinates'
import {
  streamOptimization,
  cancelOptimization,
  decodeSabB64,
  type OptimizeRequest,
} from '@/api/optimize'
import type { DosimetryStats } from '@/api/types'

/**
 * Hook that manages the optimization lifecycle:
 * - Builds the request from current stores
 * - Streams SSE events
 * - Updates simulation/optimize stores per iteration
 */
export function useOptimization() {
  const abortRef = useRef<AbortController | null>(null)

  const start = useCallback(async () => {
    const { mode, constraints } = useOptimizeStore.getState()
    if (!mode) return

    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    useOptimizeStore.getState().setRunning(true)

    const request = buildRequest(mode, constraints)
    const addNotification = useNotificationStore.getState().addNotification

    try {
      let lastPeak: number | null = null
      let firstPeak: number | null = null

      for await (const event of streamOptimization(request, controller.signal)) {
        if (controller.signal.aborted) break

        if (event.error) {
          useOptimizeStore.getState().onError(event.message ?? 'Unknown error')
          addNotification('error', `Optimization failed: ${event.message}`)
          return
        }

        if (event.done) {
          const reduction =
            firstPeak && lastPeak
              ? `${((1 - lastPeak / firstPeak) * 100).toFixed(0)}% reduction`
              : ''
          const reason = event.cancelled
            ? 'Cancelled'
            : event.reason ?? 'Converged'
          useOptimizeStore.getState().onDone(
            `${reason} after ${event.total_iters ?? event.iter ?? '?'} iterations. ${reduction}`,
          )
          return
        }

        if (event.objective !== undefined) {
          if (firstPeak === null) firstPeak = event.objective
          lastPeak = event.objective
        }

        useOptimizeStore.getState().onIteration({
          iter: event.iter ?? 0,
          objective: event.objective ?? 0,
          gradNorm: event.grad_norm,
          params: event.params ?? {},
          stats: event.stats,
          converged: event.converged,
          done: event.done,
          progress: event.progress,
          isBest: event.is_best,
        })

        // Update SAB heatmap on the body
        if (event.sab_b64) {
          const sab = decodeSabB64(event.sab_b64)
          const stats = (event.stats ?? {}) as unknown as DosimetryStats
          useSimulationStore.getState().setResults(sab, stats, {})
        }

        // Placement mode: move antenna (server Z-up to scene Y-up)
        if (mode === 'placement' && event.params?.antenna_pos) {
          const [sx, sy, sz] = event.params.antenna_pos as number[]
          // Server [x, y, z] -> Scene [x, z, -y]
          useSimulationStore.getState().setAntennaPos([sx, sz, -sy])
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      useOptimizeStore.getState().onError((err as Error).message)
      addNotification('error', `Optimization error: ${(err as Error).message}`)
    }
  }, [])

  const stop = useCallback(async () => {
    abortRef.current?.abort()
    await cancelOptimization().catch(() => {})
    useOptimizeStore.getState().setRunning(false)
  }, [])

  return { start, stop }
}

function buildRequest(
  mode: string,
  constraints: OptimizeConstraints,
): OptimizeRequest {
  const base: OptimizeRequest = {
    mode,
    max_iters: constraints.maxIters ?? 50,
  }

  if (mode === 'mimo_peak') {
    base.p_max = constraints.pMax ?? 1.0
    base.signal_threshold = constraints.signalThreshold ?? 0.0
  } else if (mode === 'tilt_power') {
    const sim = useSimulationStore.getState()
    base.icnirp_limit = constraints.icnirpLimit ?? 20.0
    base.power_init_dbm = sim.powerDbm
    base.tilt_init_deg = 0
  } else if (mode === 'placement') {
    const sim = useSimulationStore.getState()
    const pos = sim.antennaPos
    if (pos) {
      base.center = toServer(pos) as number[]
    }
    base.grid_size = constraints.gridSize ?? 5
    base.grid_spacing = constraints.gridSpacing ?? 2.0
    base.constraint_axis = constraints.constraintAxis
    base.constraint_value = constraints.constraintValue
  }

  return base
}
