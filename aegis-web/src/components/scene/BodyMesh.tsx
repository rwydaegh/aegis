import { useRef, useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { jetColor, gainTFromLinear } from '@/lib/colormap'
import { useBodyLoader } from '@/hooks/useBodyLoader'

/** Compliance color: green -> yellow -> orange -> red at thresholds 0.5, 0.8, 1.0 */
function complianceColor(ratio: number): [number, number, number] {
  ratio = Math.max(0, Math.min(1.5, ratio))
  if (ratio < 0.5) {
    // green
    return [0.29, 0.87, 0.50]
  } else if (ratio < 0.8) {
    // green -> yellow
    const u = (ratio - 0.5) / 0.3
    return [0.29 + u * (0.98 - 0.29), 0.87 + u * (0.75 - 0.87), 0.50 + u * (0.15 - 0.50)]
  } else if (ratio < 1.0) {
    // yellow -> orange/red
    const u = (ratio - 0.8) / 0.2
    return [0.98, 0.75 - u * 0.30, 0.15 - u * 0.10]
  } else {
    // red
    return [0.97, 0.44, 0.44]
  }
}

export default function BodyMesh() {
  useBodyLoader()  // triggers body fetch

  const meshRef = useRef<THREE.Mesh>(null)
  const geometry = useSceneStore(s => s.bodyGeometry)
  const sabArray = useSimulationStore(s => s.sabArray)
  const sabAveragedArray = useSimulationStore(s => s.sabAveragedArray)
  const sincArray = useSimulationStore(s => s.sincArray)
  const sincAveragedArray = useSimulationStore(s => s.sincAveragedArray)
  const compliance = useSimulationStore(s => s.stats?.compliance)
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const bodyRotationY = useSimulationStore(s => s.bodyRotationY)
  const legendScale = useUIStore(s => s.legendScale)
  const dynamicRangeDb = useUIStore(s => s.dynamicRangeDb)
  const colormapLocked = useUIStore(s => s.colormapLocked)
  const colormapLockedMax = useUIStore(s => s.colormapLockedMax)
  const sab1cm2AveragedArray = useSimulationStore(s => s.sab1cm2AveragedArray)
  const displayQuantity = useSimulationStore(s => s.displayQuantity)
  const ratioMode = useUIStore(s => s.ratioMode)

  // Pick data array based on display quantity
  const arrayMap: Record<string, Float32Array | null> = {
    sab: sabArray,
    sab_4cm2: sabAveragedArray,
    sab_1cm2: sab1cm2AveragedArray,
    sinc_local: sincArray,
  }
  let activeArray = arrayMap[displayQuantity] ?? null
  const dataArray = activeArray ?? sabArray

  // Ratio mode: find limit from compliance checks
  let isRatioMode = ratioMode && displayQuantity !== 'sab'
  let ratioLimit = 1.0
  if (isRatioMode && compliance?.checks) {
    const limitMap: Record<string, (c: { label: string }) => boolean> = {
      sab_4cm2: (c) => c.label.includes('4 cm'),
      sab_1cm2: (c) => c.label.includes('1 cm'),
      sinc_local: (c) => c.label.includes('S_inc') && c.label.includes('local'),
    }
    const finder = limitMap[displayQuantity]
    if (finder) {
      ratioLimit = compliance.checks.find(finder)?.limit ?? 20.0
    }
  }

  // Apply heatmap colors when data, scale mode, or dynamic range changes
  useEffect(() => {
    if (!geometry || !config) return

    const colorAttr = geometry.getAttribute('color') as THREE.BufferAttribute
    if (!colorAttr) return

    if (!dataArray) {
      for (let i = 0; i < colorAttr.count; i++) {
        colorAttr.setXYZ(i, 0.5, 0.5, 0.5)
      }
    } else if (isRatioMode) {
      // Compliance ratio coloring
      const nFaces = dataArray.length
      for (let f = 0; f < nFaces; f++) {
        const ratio = ratioLimit > 0 ? dataArray[f] / ratioLimit : 0
        const [r, g, b] = complianceColor(ratio)
        colorAttr.setXYZ(f * 3, r, g, b)
        colorAttr.setXYZ(f * 3 + 1, r, g, b)
        colorAttr.setXYZ(f * 3 + 2, r, g, b)
      }
    } else {
      const currentMax = Math.max(...Array.from(dataArray))

      // When lock is first activated, store the current max
      if (colormapLocked && colormapLockedMax == null) {
        useUIStore.getState().setColormapLockedMax(currentMax)
      }

      const maxSab = (colormapLocked && colormapLockedMax != null) ? colormapLockedMax : currentMax
      const nFaces = dataArray.length
      for (let f = 0; f < nFaces; f++) {
        let t: number
        if (legendScale === 'dB') {
          t = gainTFromLinear(dataArray[f], maxSab, dynamicRangeDb)
        } else {
          t = maxSab > 0 ? dataArray[f] / maxSab : 0
        }
        const [r, g, b] = jetColor(t)
        colorAttr.setXYZ(f * 3, r, g, b)
        colorAttr.setXYZ(f * 3 + 1, r, g, b)
        colorAttr.setXYZ(f * 3 + 2, r, g, b)
      }
    }
    colorAttr.needsUpdate = true
  }, [dataArray, isRatioMode, ratioLimit, geometry, config, legendScale, dynamicRangeDb, colormapLocked, colormapLockedMax])

  // Find peak triangle index for the peak location indicator
  const peakIdx = useMemo(() => {
    const arr = sabAveragedArray ?? sabArray
    if (!arr) return null
    let maxVal = -Infinity
    let maxIdx = 0
    for (let i = 0; i < arr.length; i++) {
      if (arr[i] > maxVal) { maxVal = arr[i]; maxIdx = i }
    }
    return maxIdx
  }, [sabAveragedArray, sabArray])

  // Compute peak centroid from geometry
  const peakPosition = useMemo(() => {
    if (peakIdx == null || !geometry) return null
    const posAttr = geometry.getAttribute('position') as THREE.BufferAttribute
    if (!posAttr) return null

    const baseVertex = peakIdx * 3
    if (baseVertex + 2 >= posAttr.count) return null

    let cx = 0, cy = 0, cz = 0
    for (let v = 0; v < 3; v++) {
      cx += posAttr.getX(baseVertex + v)
      cy += posAttr.getY(baseVertex + v)
      cz += posAttr.getZ(baseVertex + v)
    }
    return new THREE.Vector3(cx / 3, cy / 3, cz / 3)
  }, [peakIdx, geometry])

  if (!geometry) return null

  return (
    <group position={bodyOffset} rotation={[0, bodyRotationY, 0]}>
      <mesh
        ref={meshRef}
        geometry={geometry}
        castShadow
      >
        <meshStandardMaterial
          vertexColors
          wireframe={wireframe}
          roughness={0.7}
          metalness={0.1}
        />
      </mesh>

      {/* Peak location indicator */}
      {peakPosition && (
        <mesh position={peakPosition}>
          <sphereGeometry args={[0.015, 12, 12]} />
          <meshBasicMaterial color="#ff2222" />
        </mesh>
      )}
    </group>
  )
}
