import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { jetColor, gainTFromLinear, arrayMax } from '@/lib/colormap'
import PeakIndicator from './PeakIndicator'
import type { ScenePos } from '@/api/coordinates'
import type { DosimetryStats, ComplianceInfo } from '@/api/types'

export interface BodyMeshInstanceProps {
  geometry: THREE.BufferGeometry | null
  sabArray: Float32Array | null
  sabAveragedArray?: Float32Array | null
  sincArray?: Float32Array | null
  sab1cm2AveragedArray?: Float32Array | null
  stats?: DosimetryStats | null
  compliance?: ComplianceInfo | null
  position: ScenePos
  rotationY: number
  opacity?: number
  onClick?: () => void
}

export default function BodyMeshInstance({
  geometry,
  sabArray,
  sabAveragedArray,
  sincArray,
  sab1cm2AveragedArray,
  stats,
  compliance,
  position,
  rotationY,
  opacity = 1,
  onClick,
}: BodyMeshInstanceProps) {
  const meshRef = useRef<THREE.Mesh>(null)

  const displayQuantity = useSimulationStore(s => s.displayQuantity)
  const wireframe = useUIStore(s => s.wireframe)
  const ratioMode = useUIStore(s => s.ratioMode)
  const legendScale = useUIStore(s => s.legendScale)
  const dynamicRangeDb = useUIStore(s => s.dynamicRangeDb)
  const colormapLocked = useUIStore(s => s.colormapLocked)
  const colormapLockedMax = useUIStore(s => s.colormapLockedMax)

  // Pick data array based on display quantity
  const arrayMap: Record<string, Float32Array | null | undefined> = {
    sab: sabArray,
    sab_4cm2: sabAveragedArray,
    sab_1cm2: sab1cm2AveragedArray,
    sinc_local: sincArray,
  }
  const activeArray = arrayMap[displayQuantity] ?? null
  const dataArray = activeArray ?? sabArray

  // Ratio mode: find limit from compliance checks
  const isRatioMode = ratioMode && displayQuantity !== 'sab'
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
    if (!geometry) return

    const colorAttr = geometry.getAttribute('color') as THREE.BufferAttribute
    if (!colorAttr) return

    if (!dataArray) {
      for (let i = 0; i < colorAttr.count; i++) {
        colorAttr.setXYZ(i, 0.5, 0.5, 0.5)
      }
    } else if (isRatioMode) {
      // Ratio coloring: same jet colormap as normal mode, but values are ratio to ICNIRP limit.
      // This preserves the spatial pattern while showing ratio units on the legend.
      const nFaces = dataArray.length
      let maxRatio = 0
      for (let f = 0; f < nFaces; f++) {
        const ratio = ratioLimit > 0 ? dataArray[f] / ratioLimit : 0
        if (ratio > maxRatio) maxRatio = ratio
      }
      if (maxRatio <= 0) maxRatio = 1

      for (let f = 0; f < nFaces; f++) {
        const ratio = ratioLimit > 0 ? dataArray[f] / ratioLimit : 0
        const t = ratio / maxRatio
        const [r, g, b] = jetColor(t)
        colorAttr.setXYZ(f * 3, r, g, b)
        colorAttr.setXYZ(f * 3 + 1, r, g, b)
        colorAttr.setXYZ(f * 3 + 2, r, g, b)
      }
    } else {
      const currentMax = arrayMax(dataArray)

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
  }, [dataArray, isRatioMode, ratioLimit, geometry, legendScale, dynamicRangeDb, colormapLocked, colormapLockedMax])

  if (!geometry) return null

  return (
    <group position={position} rotation={[0, rotationY, 0]}>
      <mesh
        ref={meshRef}
        geometry={geometry}
        castShadow
        onClick={onClick}
      >
        <meshStandardMaterial
          vertexColors
          wireframe={wireframe}
          roughness={0.7}
          metalness={0.1}
          transparent={opacity < 1}
          opacity={opacity}
        />
      </mesh>

      <PeakIndicator
        geometryOverride={geometry}
        sabOverride={sabArray}
        peakValueOverride={stats?.peak_sab_averaged ?? stats?.peak_sab}
        compliantOverride={stats?.compliant}
      />
    </group>
  )
}
