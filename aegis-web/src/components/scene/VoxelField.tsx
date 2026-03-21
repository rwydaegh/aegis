import { useMemo, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useVoxelLoader } from '@/hooks/useVoxelLoader'

export default function VoxelField() {
  useVoxelLoader()

  const voxelData = useSceneStore(s => s.voxelData)
  const layerVisibility = useSceneStore(s => s.layerVisibility)
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)
  const envMode = useSceneStore(s => s.envDisplayMode)

  if (!voxelData || !config || envMode !== 'cubes') return null

  const sizeScale = config.voxels?.size_scale ?? 0.95
  const { positions, sizes, colors, materialIndices, meta } = voxelData
  const nVoxels = positions.length / 3

  // Group voxels by material
  const groups = useMemo(() => {
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

  return (
    <group>
      {Object.entries(groups).map(([matName, group]) => {
        if (!layerVisibility[matName]) return null
        if (group.indices.length === 0) return null

        return (
          <VoxelGroup
            key={matName}
            indices={group.indices}
            positions={positions}
            sizes={sizes}
            colors={colors}
            sizeScale={sizeScale}
            wireframe={wireframe}
            matColor={meta.material_colors?.[matName]}
          />
        )
      })}
    </group>
  )
}

function VoxelGroup({ indices, positions, sizes, colors, sizeScale, wireframe, matColor }: {
  indices: number[]
  positions: Float32Array
  sizes: Float32Array
  colors: Uint8Array
  sizeScale: number
  wireframe: boolean
  matColor?: [number, number, number]
}) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const count = indices.length

  useEffect(() => {
    if (!meshRef.current) return

    const dummy = new THREE.Object3D()
    const color = new THREE.Color()

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

      // Use per-voxel color from binary data
      const r = colors[i * 3] / 255
      const g = colors[i * 3 + 1] / 255
      const b = colors[i * 3 + 2] / 255
      color.setRGB(r, g, b)
      meshRef.current.setColorAt(j, color)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
    if (meshRef.current.instanceColor) meshRef.current.instanceColor.needsUpdate = true
  }, [indices, positions, sizes, colors, sizeScale])

  // matColor is available for future use (e.g., override per-material color)
  void matColor

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]} castShadow receiveShadow>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial vertexColors wireframe={wireframe} roughness={0.8} />
    </instancedMesh>
  )
}
