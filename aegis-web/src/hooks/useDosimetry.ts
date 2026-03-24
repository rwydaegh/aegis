import { useEffect, useRef, useCallback } from 'react'
import { useShallow } from 'zustand/react/shallow'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useNotificationStore } from '@/stores/notifications'
import { computeDosimetry, computeVoxelRT, computeRT, computeSionnaRT, type RtConfig } from '@/api/client'

export function useDosimetry() {
  const sim = useSimulationStore(useShallow(s => ({
    antennaPos: s.antennaPos,
    mode: s.mode,
    fresnel: s.fresnel,
    polarisation: s.polarisation,
    curvature: s.curvature,
    diffraction: s.diffraction,
    powerDbm: s.powerDbm,
    skinModel: s.skinModel,
    freqGhz: s.freqGhz,
    nPaths: s.nPaths,
    bodyOffset: s.bodyOffset,
    bodyRotationY: s.bodyRotationY,
    stochasticPreset: s.stochasticPreset,
    stochasticOverrides: s.stochasticOverrides,
    stochasticSeed: s.stochasticSeed,
    enabledQuantities: s.enabledQuantities,
  })))

  const exposureScenario = useUIStore(s => s.exposureScenario)

  const scene = useSceneStore(useShallow(s => ({
    bodyName: s.bodyName,
    config: s.viewerConfig,
    caps: s.capabilities,
    pathSource: s.pathSource,
    rtSource: s.rtSource,
    rtMaxOrder: s.rtMaxOrder,
    loadedScenePath: s.loadedScenePath,
    rtConfig: s.rtConfig,
  })))

  const abortRef = useRef<AbortController | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const generationRef = useRef(0)

  const triggerCompute = useCallback(() => {
    if (!sim.antennaPos || !scene.config) return

    // Abort any in-flight request
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    const gen = ++generationRef.current
    const setComputing = useUIStore.getState().setComputing
    setComputing(true)

    // Send antenna tip position (not pole base) to the backend for physics
    const poleH = scene.config.antenna.pole_height ?? 2
    const antennaTip: typeof sim.antennaPos = [sim.antennaPos[0], sim.antennaPos[1] + poleH, sim.antennaPos[2]]

    const params = {
      antennaPos: antennaTip,
      bodyOffset: sim.bodyOffset,
      bodyRotationY: sim.bodyRotationY,
      mode: sim.mode,
      fresnel: sim.fresnel,
      polarisation: sim.polarisation,
      curvature: sim.curvature,
      diffraction: sim.diffraction,
      powerDbm: sim.powerDbm,
      skinModel: sim.skinModel,
      freqGhz: sim.freqGhz,
      nPaths: sim.nPaths,
      stochastic: scene.pathSource === 'stochastic',
      stochasticPreset: sim.stochasticPreset,
      stochasticOverrides: sim.stochasticOverrides,
      stochasticSeed: sim.stochasticSeed,
      quantities: Array.from(sim.enabledQuantities) as string[],
      exposureScenario,
      bodyName: scene.bodyName || undefined,
    }

    // Timeout: abort after configured limit
    const timeoutMs = 60000
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

    // Build RT config from store state
    const rc = scene.rtConfig
    const rtCfg: RtConfig = {
      max_depth: scene.rtMaxOrder,
      method: rc.method,
      rays_per_source: rc.raysPerSource,
      max_paths_per_source: rc.maxPathsPerSource,
      los: rc.los,
      specular_reflection: rc.specularReflection,
      diffuse_reflection: rc.diffuseReflection,
      refraction: rc.refraction,
      diffraction: rc.diffraction,
      edge_diffraction: rc.edgeDiffraction,
      diffraction_lit_region: rc.diffractionLitRegion,
      reflection_loss_per_order: rc.reflectionLoss,
      synthetic_array: rc.syntheticArray,
      seed: rc.seed,
    }

    // Choose endpoint based on path source
    let computeCall: Promise<import('@/api/client').ComputeResult>
    if (scene.pathSource === 'rt' && scene.rtSource === 'voxel') {
      computeCall = computeVoxelRT({ ...params, rtConfig: rtCfg }, controller.signal)
    } else if (scene.pathSource === 'rt' && scene.rtSource === 'differt' && scene.loadedScenePath) {
      computeCall = computeRT({ ...params, scenePath: scene.loadedScenePath, rtConfig: rtCfg }, controller.signal)
    } else if (scene.pathSource === 'rt' && scene.rtSource === 'sionna' && scene.loadedScenePath) {
      computeCall = computeSionnaRT({ ...params, scenePath: scene.loadedScenePath, rtConfig: rtCfg }, controller.signal)
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
        if (stats.compliance) {
          useSimulationStore.getState().setCompliance(stats.compliance)
        }
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
        useNotificationStore.getState().addNotification('error', `Compute failed: ${(err as Error).message ?? err}`)
      })
      .finally(() => {
        clearTimeout(timeoutId)
        if (gen === generationRef.current) setComputing(false)
      })
  }, [sim, scene, exposureScenario])

  // Debounced trigger on any dependency change
  useEffect(() => {
    if (!sim.antennaPos) return

    if (timerRef.current) clearTimeout(timerRef.current)
    const debounceMs = scene.config?.interaction?.debounce_ms ?? 200
    timerRef.current = setTimeout(triggerCompute, debounceMs)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [sim, scene, exposureScenario, triggerCompute])

  // Cancel any in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])
}
