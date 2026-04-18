import { useMemo, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useVoxelLoader } from '@/hooks/useVoxelLoader'
import { useClickToPlace } from '@/hooks/useClickToPlace'

// Default material colors - must match src/aegis/viewer/default_config.json voxels.material_colors
const DEFAULT_MATERIAL_COLORS: Record<string, [number, number, number]> = {
  concrete: [180, 180, 180],
  asphalt: [80, 80, 80],
  vegetation: [40, 160, 40],
  water: [30, 100, 220],
  brick: [200, 80, 50],
  glass: [150, 210, 240],
  metal: [160, 160, 170],
  wood: [160, 120, 80],
}

export default function VoxelField() {
  useVoxelLoader()

  const voxelData = useSceneStore(s => s.voxelData)
  const layerVisibility = useSceneStore(s => s.layerVisibility)
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)
  const envMode = useSceneStore(s => s.envDisplayMode)

  // Group voxels by material (hook must run unconditionally)
  const groups = useMemo(() => {
    if (!voxelData) return null
    const { materialIndices, meta } = voxelData
    const nVoxels = voxelData.positions.length / 3
    const result: Record<string, { indices: number[] }> = {}
    for (const mat of meta.materials) {
      result[mat] = { indices: [] }
    }
    for (let i = 0; i < nVoxels; i++) {
      const matIdx = materialIndices[i]
      const matName = meta.materials[matIdx]
      if (matName && result[matName]) {
        result[matName].indices.push(i)
      }
    }
    return result
  }, [voxelData])

  const clickHandlers = useClickToPlace()

  if (!voxelData || !config || !groups || envMode !== 'cubes') return null

  const sizeScale = config.voxels?.size_scale ?? 0.95
  const configMatColors = config.voxels?.material_colors

  return (
    <group {...clickHandlers}>
      {Object.entries(groups).map(([matName, group]) => {
        if (!layerVisibility[matName]) return null
        if (group.indices.length === 0) return null

        const mc = configMatColors?.[matName] ?? DEFAULT_MATERIAL_COLORS[matName] ?? [200, 200, 200]

        return (
          <VoxelGroup
            key={matName}
            indices={group.indices}
            positions={voxelData.positions}
            sizes={voxelData.sizes}
            sizeScale={sizeScale}
            wireframe={wireframe}
            materialColor={mc}
          />
        )
      })}
    </group>
  )
}

function VoxelGroup({ indices, positions, sizes, sizeScale, wireframe, materialColor }: {
  indices: number[]
  positions: Float32Array
  sizes: Float32Array
  sizeScale: number
  wireframe: boolean
  materialColor: [number, number, number]
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const count = indices.length
  const color = useMemo(
    () => new THREE.Color(materialColor[0] / 255, materialColor[1] / 255, materialColor[2] / 255),
    [materialColor],
  )

  useEffect(() => {
    if (!meshRef.current) return

    const dummy = new THREE.Object3D()

    for (let j = 0; j < count; j++) {
      const i = indices[j]
      const x = positions[i * 3]
      const y = positions[i * 3 + 1]
      const z = positions[i * 3 + 2]
      const s = sizes[i] * sizeScale

      dummy.position.set(x, y, z)
      dummy.scale.set(s, s, s)
      dummy.updateMatrix()
      meshRef.current.setMatrixAt(j, dummy.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [indices, positions, sizes, sizeScale, count])

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]} castShadow receiveShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color={color} wireframe={wireframe} roughness={0.8} flatShading />
    </instancedMesh>
  )
}
