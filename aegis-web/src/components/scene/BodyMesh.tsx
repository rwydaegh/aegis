import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { sampleInferno, gainTFromLinear } from '@/lib/colormap'
import { useBodyLoader } from '@/hooks/useBodyLoader'

export default function BodyMesh() {
  useBodyLoader()  // triggers body fetch

  const meshRef = useRef<THREE.Mesh>(null)
  const geometry = useSceneStore(s => s.bodyGeometry)
  const sabArray = useSimulationStore(s => s.sabArray)
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)
  const legendScale = useUIStore(s => s.legendScale)

  // Apply heatmap colors when sabArray or scale mode changes
  useEffect(() => {
    if (!geometry || !config) return

    const colorAttr = geometry.getAttribute('color') as THREE.BufferAttribute
    if (!colorAttr) return

    const stops = config.colormap.stops
    const dynamicRangeDb = (config.colormap as any).dynamic_range_db ?? 40

    if (!sabArray) {
      // No results: neutral gray
      for (let i = 0; i < colorAttr.count; i++) {
        colorAttr.setXYZ(i, 0.5, 0.5, 0.5)
      }
    } else {
      const maxSab = Math.max(...Array.from(sabArray))
      const nFaces = sabArray.length
      for (let f = 0; f < nFaces; f++) {
        let t: number
        if (legendScale === 'dB') {
          t = gainTFromLinear(sabArray[f], maxSab, dynamicRangeDb)
        } else {
          t = maxSab > 0 ? sabArray[f] / maxSab : 0
        }
        const [r, g, b] = sampleInferno(t, stops)
        colorAttr.setXYZ(f * 3, r, g, b)
        colorAttr.setXYZ(f * 3 + 1, r, g, b)
        colorAttr.setXYZ(f * 3 + 2, r, g, b)
      }
    }
    colorAttr.needsUpdate = true
  }, [sabArray, geometry, config, legendScale])

  if (!geometry) return null

  return (
    <mesh
      ref={meshRef}
      geometry={geometry}
      position={bodyOffset}
      rotation={[0, bodyRotationY, 0]}
      castShadow
    >
      <meshStandardMaterial
        vertexColors
        wireframe={wireframe}
        roughness={0.7}
        metalness={0.1}
      />
    </mesh>
  )
}
