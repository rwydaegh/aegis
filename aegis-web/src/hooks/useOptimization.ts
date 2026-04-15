import { useCallback, useRef } from 'react'
import { useOptimizeStore, type OptimizeConstraints } from '@/stores/optimize'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
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

    if (mode === 'placement') {
      const pos = useSimulationStore.getState().antennaPos
      if (pos) {
        useOptimizeStore.getState().setPlacementCenter([...pos] as [number, number, number])
      }
    }

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
          if (stats.path_viz) {
            useSceneStore.getState().setRtPaths(stats.path_viz)
          }
        }

        // Placement mode: move antenna (server Z-up to scene Y-up)
        const placementPos =
          mode === 'placement' && event.done && Array.isArray(event.best?.antenna_pos)
            ? (event.best.antenna_pos as number[])
            : (event.params?.antenna_pos as number[] | undefined)
        if (mode === 'placement' && placementPos) {
          const [sx, sy, sz] = placementPos
          // Server [x, y, z] -> Scene [x, z, -y]
          useSimulationStore.getState().setAntennaPos([sx, sz, -sy])
        }

        if (event.done) {
          const reduction =
            firstPeak !== null && lastPeak !== null
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
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return
      useOptimizeStore.getState().onError((err as Error).message)
      addNotification('error', `Optimization error: ${(err as Error).message}`)
    } finally {
      useOptimizeStore.getState().setRunning(false)
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
    const scene = useSceneStore.getState()
    const pos = sim.antennaPos
    if (pos) {
      base.center = toServer(pos) as number[]
    }
    base.grid_size = constraints.gridSize ?? 5
    base.grid_spacing = constraints.gridSpacing ?? 2.0
    base.constraint_axis = constraints.constraintAxis
    base.constraint_value = constraints.constraintValue
    base.body_name = scene.bodyName || undefined
    base.body_offset = toServer(sim.bodyOffset)
    base.body_rotation_y = sim.bodyRotationY
    base.power_dbm = sim.powerDbm
    base.skin_model = sim.skinModel
    base.freq_hz = sim.freqGhz * 1e9
    base.dosimetry_mode = sim.mode
    base.fresnel = sim.fresnel
    base.polarisation = sim.polarisation
    base.curvature = sim.curvature
    base.diffraction = sim.diffraction
    base.scene_path = scene.loadedScenePath || undefined
    base.rt_config = {
      max_depth: scene.rtMaxOrder,
      method: scene.rtConfig.method,
      rays_per_source: scene.rtConfig.raysPerSource,
      max_paths_per_source: scene.rtConfig.maxPathsPerSource,
      chunk_size: scene.rtConfig.chunkSize,
      los: scene.rtConfig.los,
      specular_reflection: scene.rtConfig.specularReflection,
      diffuse_reflection: scene.rtConfig.diffuseReflection,
      refraction: scene.rtConfig.refraction,
      diffraction: scene.rtConfig.diffraction,
      edge_diffraction: scene.rtConfig.edgeDiffraction,
      diffraction_lit_region: scene.rtConfig.diffractionLitRegion,
      reflection_loss_per_order: scene.rtConfig.reflectionLoss,
      synthetic_array: scene.rtConfig.syntheticArray,
      seed: scene.rtConfig.seed,
    }
  }

  return base
}
