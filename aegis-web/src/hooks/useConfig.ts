import { useState, useEffect } from 'react'
import { fetchViewerConfig, fetchCapabilities } from '@/api/client'
import { toScene } from '@/api/coordinates'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import type { ScenePos } from '@/api/coordinates'

type ConfigStatus = 'loading' | 'ready' | 'error'

export function useConfig() {
  const [status, setStatus] = useState<ConfigStatus>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchViewerConfig(), fetchCapabilities()])
      .then(([config, caps]) => {
        useSceneStore.setState({ viewerConfig: config, capabilities: caps })

        const defaultLevel = config.dosimetry?.fidelity_levels?.[2]?.value ?? 2
        const simState: Record<string, unknown> = {
          level: defaultLevel,
          powerDbm: 30,
          tissue: 'skin_28ghz',
          nPaths: config.dosimetry?.path_options?.[0]?.value ?? 1,
        }

        // Auto-place body at the recommended position (if location was loaded)
        // body_placement is already in Y-up (scene) coordinates
        const bp = (caps as any).body_placement as [number, number, number] | null
        if (bp) {
          simState.bodyOffset = bp as ScenePos
        }

        useSimulationStore.setState(simState)

        // Load available scene paths
        if ((caps as any).scenes?.length > 0) {
          useSceneStore.setState({ scenePaths: (caps as any).scenes })
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
