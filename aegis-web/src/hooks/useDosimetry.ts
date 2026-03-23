import { useEffect, useRef, useCallback } from 'react'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { computeDosimetry, computeVoxelRT, computeRT, computeSionnaRT } from '@/api/client'

export function useDosimetry() {
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const mode = useSimulationStore(s => s.mode)
  const fresnel = useSimulationStore(s => s.fresnel)
  const polarisation = useSimulationStore(s => s.polarisation)
  const curvature = useSimulationStore(s => s.curvature)
  const diffraction = useSimulationStore(s => s.diffraction)
  const powerDbm = useSimulationStore(s => s.powerDbm)
  const skinModel = useSimulationStore(s => s.skinModel)
  const freqGhz = useSimulationStore(s => s.freqGhz)
  const nPaths = useSimulationStore(s => s.nPaths)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)
  const stochasticPreset = useSimulationStore(s => s.stochasticPreset)
  const stochasticOverrides = useSimulationStore(s => s.stochasticOverrides)
  const stochasticSeed = useSimulationStore(s => s.stochasticSeed)
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)

  const exposureScenario = useUIStore(s => s.exposureScenario)

  const config = useSceneStore(s => s.viewerConfig)
  const caps = useSceneStore(s => s.capabilities)
  const pathSource = useSceneStore(s => s.pathSource)
  const rtSource = useSceneStore(s => s.rtSource)
  const rtMaxOrder = useSceneStore(s => s.rtMaxOrder)
  const loadedScenePath = useSceneStore(s => s.loadedScenePath)

  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generationRef = useRef(0)

  const triggerCompute = useCallback(() => {
    if (!antennaPos || !config) return

    // Abort any in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const gen = ++generationRef.current
    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    // Send antenna tip position (not pole base) to the backend for physics
    const poleH = (config.antenna as Record<string, unknown>)?.pole_height as number ?? 2
    const antennaTip: typeof antennaPos = [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]

    const params = {
      antennaPos: antennaTip,
      bodyOffset,
      bodyRotationY,
      mode,
      fresnel,
      polarisation,
      curvature,
      diffraction,
      powerDbm,
      skinModel,
      freqGhz,
      nPaths,
      stochastic: pathSource === 'stochastic',
      stochasticPreset,
      stochasticOverrides,
      stochasticSeed,
      quantities: Array.from(enabledQuantities) as string[],
      exposureScenario,
    }

    // Timeout: abort after configured limit
    const timeoutMs = (config.interaction as Record<string, unknown> & { compute_timeout_ms?: number }).compute_timeout_ms ?? 60000
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

    // Choose endpoint based on path source
    let computeCall: Promise<import('@/api/client').ComputeResult>
    if (pathSource === 'rt' && rtSource === 'voxel') {
      computeCall = computeVoxelRT({ ...params, maxOrder: rtMaxOrder }, controller.signal)
    } else if (pathSource === 'rt' && rtSource === 'differt' && loadedScenePath) {
      computeCall = computeRT({ ...params, scenePath: loadedScenePath, maxOrder: rtMaxOrder }, controller.signal)
    } else if (pathSource === 'rt' && rtSource === 'sionna' && loadedScenePath) {
      computeCall = computeSionnaRT({ ...params, scenePath: loadedScenePath }, controller.signal)
    } else {
      computeCall = computeDosimetry(params, controller.signal)
    }

    const t_request = performance.now()
    computeCall
      .then(({ sab, stats, arrays }) => {
        const t_response = performance.now()
        if (gen !== generationRef.current) return // stale response
        useSimulationStore.getState().setResults(sab, stats, {
          sabAveraged: arrays['sab_4cm2'],
          sinc: arrays['sinc_local'],
          sincAveraged: arrays['sinc_averaged'],
          sab1cm2Averaged: arrays['sab_1cm2'],
        })
        if (stats.path_viz) {
          useSceneStore.getState().setRtPaths(stats.path_viz)
        }

        // Compute timing breakdown for the UI
        const networkMs = (t_response - t_request) - (stats.timings?.route_total_ms ?? 0)
        const t = stats.timings
        useUIStore.getState().setLastComputeTiming({
          totalMs: t_response - t_request,
          rtMs: t?.rt_ms ?? null,
          kernelMs: t?.kernel_ms ?? 0,
          averagingMs: (t?.avg_build_G_4cm2_ms ?? 0) + (t?.avg_matvec_4cm2_ms ?? 0),
          complianceMs: t?.compliance_stats_ms ?? 0,
          networkMs: Math.max(0, networkMs),
          avgCached: (t?.avg_build_G_4cm2_ms ?? 999) < 1,
        })
      })
      .catch(err => {
        if ((err as Error).name === 'AbortError') return // expected cancellation
        console.error('Dosimetry compute failed:', err)
      })
      .finally(() => {
        clearTimeout(timeoutId)
        if (gen === generationRef.current) setComputing(false)
      })
  }, [antennaPos, mode, fresnel, polarisation, curvature, diffraction, powerDbm, skinModel, freqGhz, nPaths,
    bodyOffset, bodyRotationY, config, caps, pathSource, rtSource, rtMaxOrder, loadedScenePath,
    stochasticPreset, stochasticOverrides, stochasticSeed, enabledQuantities, exposureScenario])

  // Debounced trigger on any dependency change
  useEffect(() => {
    if (!antennaPos) return

    if (timerRef.current) clearTimeout(timerRef.current)
    const debounceMs = config?.interaction?.debounce_ms ?? 200
    timerRef.current = setTimeout(triggerCompute, debounceMs)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [antennaPos, mode, fresnel, polarisation, curvature, diffraction, powerDbm, skinModel, freqGhz, nPaths,
    bodyOffset, bodyRotationY, triggerCompute, config, stochasticPreset, stochasticOverrides,
    stochasticSeed, pathSource, enabledQuantities, exposureScenario])

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])
}
