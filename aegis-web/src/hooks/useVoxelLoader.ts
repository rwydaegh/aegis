import { useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { fetchVoxels } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useNotificationStore } from '@/stores/notifications'
import { buildHeightmap } from '@/lib/physics'
export function useVoxelLoader() {
  const caps = useSceneStore(s => s.capabilities)

  useEffect(() => {
    if (!caps?.has_voxels) return

    const controller = new AbortController()

    fetchVoxels(controller.signal).then(({ binary, meta }) => {
      if (controller.signal.aborted) return
      useSceneStore.setState({
        voxelData: { ...binary, meta },
        layerVisibility: Object.fromEntries(meta.materials.map(m => [m, true])),
        sceneGeometry: null,
        loadedScenePath: '',
      })

      // Build heightmap for physics collision
      const config = useSceneStore.getState().viewerConfig
      const resFactor = config?.voxels?.heightmap_resolution_factor ?? 1
      const hmFn = buildHeightmap(binary.positions, binary.sizes, resFactor)
      useSceneStore.setState({ voxelHeightmap: hmFn })

      // Auto-place body if body_placement available
      // body_placement is already in Y-up (scene) coordinates from the server
      const bp = caps.body_placement
      if (bp) {
        useSimulationStore.getState().setBodyOffset(bp)
      }
    }).catch(err => {
      if ((err as Error).name === 'AbortError') return
      const msg = (err as Error).message ?? ''
      // 404 means voxels were cleared from the backend (cache clear, server restart,
      // worker mismatch). This is expected during scene transitions, not a real error.
      if (msg.includes('No voxel data loaded')) {
        const prev = useSceneStore.getState().capabilities
        if (prev) {
          useSceneStore.setState({ capabilities: { ...prev, has_voxels: false } })
        }
        return
      }
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', `Failed to load voxels: ${msg}`)
    })

    return () => { controller.abort() }
  }, [caps?.has_voxels])
}
