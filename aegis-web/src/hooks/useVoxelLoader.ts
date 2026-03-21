import { useEffect } from 'react'
import { fetchVoxels } from '@/api/client'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { buildHeightmap } from '@/lib/physics'
import { toScene } from '@/api/coordinates'

export function useVoxelLoader() {
  const caps = useSceneStore(s => s.capabilities)

  useEffect(() => {
    if (!caps?.has_voxels) return

    fetchVoxels().then(({ binary, meta }) => {
      useSceneStore.setState({
        voxelData: { ...binary, meta },
        layerVisibility: Object.fromEntries(meta.materials.map(m => [m, true])),
      })

      // Build heightmap for physics collision
      const config = useSceneStore.getState().viewerConfig
      const resFactor = config?.voxels?.heightmap_resolution_factor ?? 1
      const hmFn = buildHeightmap(binary.positions, binary.sizes, resFactor)
      useSceneStore.setState({ voxelHeightmap: hmFn })

      // Auto-place body if body_placement available
      const bp = caps.body_placement
      if (bp) {
        const [x, y, z] = toScene(bp)
        useSimulationStore.getState().setBodyOffset([x, y, z])
      }
    }).catch(err => {
      console.error('Failed to load voxels:', err)
    })
  }, [caps?.has_voxels])
}
