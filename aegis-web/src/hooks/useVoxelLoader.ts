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

    fetchVoxels().then(({ binary, meta }) => {
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
      Sentry.captureException(err)
      useNotificationStore.getState().addNotification('error', `Failed to load voxels: ${(err as Error).message}`)
    })
  }, [caps?.has_voxels])
}
