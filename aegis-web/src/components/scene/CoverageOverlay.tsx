import { useState, useEffect } from 'react'
import * as THREE from 'three'
import { useBaseStationsStore } from '../../stores/basestations'

export function CoverageOverlay() {
  const showCoverage = useBaseStationsStore(s => s.showCoverage)
  const coverageUrl = useBaseStationsStore(s => s.coverageUrl)
  const [texture, setTexture] = useState<THREE.Texture | null>(null)

  useEffect(() => {
    if (!coverageUrl) {
      setTexture(null)
      return
    }
    const loader = new THREE.TextureLoader()
    loader.load(coverageUrl, (tex) => {
      tex.minFilter = THREE.LinearFilter
      tex.magFilter = THREE.LinearFilter
      setTexture(tex)
    })
    return () => {
      if (texture) texture.dispose()
    }
  }, [coverageUrl]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!showCoverage || !texture) return null

  // Render a plane at y=0.01 (just above ground), facing up
  // Size is approximate (200m x 200m) -- V1 does not have geo-referenced bounds
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
      <planeGeometry args={[200, 200]} />
      <meshBasicMaterial
        map={texture}
        transparent
        opacity={0.7}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}
