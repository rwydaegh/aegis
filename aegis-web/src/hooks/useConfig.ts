import { useState, useEffect } from 'react'
import { fetchViewerConfig, fetchCapabilities } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'

type ConfigStatus = 'loading' | 'ready' | 'error'

export function useConfig() {
  const [status, setStatus] = useState<ConfigStatus>('loading')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([fetchViewerConfig(), fetchCapabilities()])
      .then(([config, caps]) => {
        useSceneStore.setState({ viewerConfig: config, capabilities: caps })

        const defaultLevel = config.dosimetry?.fidelity_levels?.[2]?.value ?? 2
        useSimulationStore.setState({
          level: defaultLevel,
          powerDbm: 30,
          tissue: 'skin_28ghz',
          nPaths: config.dosimetry?.path_options?.[0]?.value ?? 1,
        })

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
