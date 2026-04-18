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
  type SSEEvent,
} from '@/api/optimize'
import type { DosimetryStats } from '@/api/types'

// -----------------------------------------------------------------------------
// Module-scope helpers (outside the hook so they can be tested in isolation
// and so they don't re-create on every render).
// -----------------------------------------------------------------------------

export type Peaks = {
  firstPeak: number | null
  lastPeak: number | null
  firstSab: number | null
  lastSab: number | null
  lastParams: Record<string, unknown> | null
}

/**
 * Update peak trackers and push iteration state / SAB heatmap to stores.
 * Returns the new peaks so the caller can thread them through the loop.
 */
export function handleIterationEvent(event: SSEEvent, peaks: Peaks): Peaks {
  let { firstPeak, lastPeak, firstSab, lastSab, lastParams } = peaks
  if (event.objective !== undefined) {
    if (firstPeak === null) firstPeak = event.objective
    lastPeak = event.objective
  }
  const peakSab = (event.stats as { peak_sab?: number } | undefined)?.peak_sab
  if (typeof peakSab === 'number' && Number.isFinite(peakSab)) {
    if (firstSab === null) firstSab = peakSab
    lastSab = peakSab
  }
  if (event.params && typeof event.params === 'object') {
    lastParams = event.params as Record<string, unknown>
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

  return { firstPeak, lastPeak, firstSab, lastSab, lastParams }
}

/**
 * Placement mode: move the antenna to the optimizer-proposed position.
 * Server uses Z-up [x, y, z]; the scene uses Y-up [x, z, -y].
 */
export function applyPlacementMove(event: SSEEvent, mode: string): void {
  if (mode !== 'placement') return

  const placementPos = event.done && Array.isArray(event.best?.antenna_pos)
    ? (event.best.antenna_pos as number[])
    : (event.params?.antenna_pos as number[] | undefined)

  if (!placementPos) return
  const [sx, sy, sz] = placementPos
  useSimulationStore.getState().setAntennaPos([sx, sz, -sy])
}

function reductionText(first: number | null, last: number | null): string {
  if (first === null || last === null || first === 0) return ''
  const pct = (1 - last / first) * 100
  if (!Number.isFinite(pct)) return ''
  return `${pct.toFixed(0)}% reduction`
}

function tiltPowerSummary(peaks: Peaks): string {
  const tilt = peaks.lastParams?.tilt_deg
  const power = peaks.lastParams?.power_dbm
  const parts: string[] = []
  if (typeof tilt === 'number' && Number.isFinite(tilt)) {
    parts.push(`tilt ${tilt.toFixed(1)}°`)
  }
  if (typeof power === 'number' && Number.isFinite(power)) {
    parts.push(`power ${power.toFixed(1)} dBm`)
  }
  if (peaks.lastSab !== null && Number.isFinite(peaks.lastSab)) {
    parts.push(`peak ${peaks.lastSab.toExponential(2)} W/m²`)
  }
  return parts.join(', ')
}

/**
 * Final event: build the summary string and notify the optimize store.
 *
 * Summary style is mode-specific because the "objective" values aren't
 * directly comparable across modes:
 *  - placement/mimo_peak minimize a positive exposure metric, so "% reduction"
 *    of the objective is meaningful.
 *  - tilt_power minimizes a signed penalty (−power + λ·violation²) which can
 *    flip sign; "% reduction" of it is nonsensical. Report final tilt, power,
 *    and peak exposure instead.
 */
export function handleDoneEvent(event: SSEEvent, peaks: Peaks, mode: string): void {
  const reason = event.cancelled ? 'Cancelled' : event.reason ?? 'Converged'
  const iters = event.total_iters ?? event.iter ?? '?'

  let detail: string
  if (mode === 'tilt_power') {
    detail = tiltPowerSummary(peaks)
  } else {
    detail = reductionText(peaks.firstPeak, peaks.lastPeak)
  }

  const message = detail
    ? `${reason} after ${iters} iterations. ${detail}`
    : `${reason} after ${iters} iterations.`
  useOptimizeStore.getState().onDone(message)
}

function buildPlacementRequest(base: OptimizeRequest, constraints: OptimizeConstraints): void {
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
    buildPlacementRequest(base, constraints)
  }

  return base
}

// -----------------------------------------------------------------------------
// Hook
// -----------------------------------------------------------------------------

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
    const isCurrent = () => abortRef.current === controller

    useOptimizeStore.getState().beginRun()
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
      let peaks: Peaks = {
        firstPeak: null,
        lastPeak: null,
        firstSab: null,
        lastSab: null,
        lastParams: null,
      }

      for await (const event of streamOptimization(request, controller.signal)) {
        if (controller.signal.aborted) break

        if (event.error) {
          if (isCurrent()) {
            useOptimizeStore.getState().onError(event.message ?? 'Unknown error')
            addNotification('error', `Optimization failed: ${event.message}`)
          }
          return
        }

        if (!isCurrent()) return
        peaks = handleIterationEvent(event, peaks)
        applyPlacementMove(event, mode)

        if (event.done) {
          if (isCurrent()) handleDoneEvent(event, peaks, mode)
          return
        }
      }
      if (controller.signal.aborted && isCurrent()) {
        useOptimizeStore.getState().onDone('Cancelled by user')
        addNotification('info', 'Optimization cancelled')
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        if (isCurrent()) {
          useOptimizeStore.getState().onDone('Cancelled by user')
          addNotification('info', 'Optimization cancelled')
        }
        return
      }
      if (isCurrent()) {
        useOptimizeStore.getState().onError((err as Error).message)
        addNotification('error', `Optimization error: ${(err as Error).message}`)
      }
    } finally {
      if (isCurrent()) {
        useOptimizeStore.getState().setRunning(false)
      }
    }
  }, [])

  const stop = useCallback(async () => {
    // Writes to the optimize store are owned by the in-flight start():
    // its AbortError catch/finally will set running=false and summary.
    // Writing here would stomp a rapid stop()-then-start() sequence.
    abortRef.current?.abort()
    await cancelOptimization().catch(() => {})
  }, [])

  return { start, stop }
}
