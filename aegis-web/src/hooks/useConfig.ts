import { useState, useEffect } from 'react'
import { fetchViewerConfig, fetchCapabilities } from '@/api/client'
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
        useSceneStore.setState({
          viewerConfig: config,
          capabilities: caps,
          bodyName: (caps as any).body_name ?? caps.bodies?.[0] ?? '',
        })

        const simState: Record<string, unknown> = {
          mode: 'spatial',
          fresnel: true,
          powerDbm: 30,
          skinModel: 'itis',
          nPaths: config.dosimetry?.path_options?.[0]?.value ?? 1,
        }

        // Auto-place body at the recommended position (if location was loaded)
        // body_placement is already in Y-up (scene) coordinates
        const bp = (caps as any).body_placement as [number, number, number] | null
        if (bp) {
          simState.bodyOffset = bp as ScenePos
        }

        useSimulationStore.setState(simState)

        // Load available scenes (server returns {name, path} objects)
        const rawScenes = (caps as any).scenes
        if (rawScenes?.length > 0) {
          const scenes = rawScenes.map((s: any) =>
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
