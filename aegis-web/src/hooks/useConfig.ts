import { useState, useEffect } from 'react'
import { fetchViewerConfig, fetchCapabilities } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import type { ScenePos } from '@/api/coordinates'

type ConfigStatus = 'loading' | 'ready' | 'error'

export function useConfig() {
  const [status, setStatus] = useState<ConfigStatus>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchViewerConfig(), fetchCapabilities()])
      .then(([config, caps]) => {
        useSceneStore.setState({
          viewerConfig: config,
          capabilities: caps,
          bodyName: caps.body_name ?? caps.bodies?.[0] ?? '',
        })

        const simState: Record<string, unknown> = {
          mode: 'spatial',
          fresnel: true,
          powerDbm: 60,
          skinModel: 'itis',
          nPaths: config.dosimetry?.path_options?.[0]?.value ?? 1,
        }

        // Auto-place body at the recommended position (if location was loaded)
        // body_placement is already in Y-up (scene) coordinates
        if (caps.body_placement) {
          simState.bodyOffset = caps.body_placement as ScenePos
        }

        useSimulationStore.setState(simState)

        // Wire config keys from DEFAULTS that are not already wired above
        const sim = useSimulationStore.getState()
        const ui = useUIStore.getState()

        if ((config.dosimetry as Record<string, unknown>)?.freq_hz) {
          sim.setFreqGhz((config.dosimetry as unknown as { freq_hz: number }).freq_hz / 1e9)
        }
        if ((config.dosimetry as unknown as { default_power_dbm?: number }).default_power_dbm !== undefined) {
          sim.setPowerDbm((config.dosimetry as unknown as { default_power_dbm: number }).default_power_dbm)
        }
        if ((config.dosimetry as unknown as { exposure_scenario?: string }).exposure_scenario) {
          const scenario = (config.dosimetry as unknown as { exposure_scenario: string }).exposure_scenario
          if (scenario === 'general_public' || scenario === 'occupational') {
            ui.setExposureScenario(scenario)
          }
        }

        // Load available scenes (server returns {name, path} objects)
        if (caps.scenes?.length > 0) {
          const scenes = caps.scenes.map((s) =>
            typeof s === 'string' ? { name: s.split(/[/\\]/).pop()?.replace('.xml', '') ?? s, path: s } : { name: s.name, path: s.path }
          )
          useSceneStore.setState({ scenes })
        }

        setStatus('ready')
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Unknown error'
        setError(message)
        setStatus('error')
      })
  }, [])

  return { status, error }
}
