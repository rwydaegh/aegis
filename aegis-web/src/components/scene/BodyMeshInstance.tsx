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
  sincAveragedArray?: Float32Array | null
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
  sincAveragedArray,
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
    sinc_wb: sincAveragedArray,
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
      sinc_wb: (c) => c.label.includes('S_inc') && c.label.includes('whole-body'),
    }
    const finder = limitMap[displayQuantity]
    if (finder) {
      ratioLimit = compliance.checks.find(finder)?.limit ?? 20.0
    }
  }

  // Apply heatmap colors when data, scale mode, or dynamic range changes.
  // Writes directly to the typed array backing the BufferAttribute for
  // performance (avoids per-vertex setXYZ overhead for large meshes).
  useEffect(() => {
    if (!geometry) return

    const colorAttr = geometry.getAttribute('color') as THREE.BufferAttribute
    if (!colorAttr) return
    const buf = colorAttr.array as Float32Array

    if (!dataArray) {
      buf.fill(0.5)
    } else if (isRatioMode) {
      const nFaces = dataArray.length
      const invLimit = ratioLimit > 0 ? 1 / ratioLimit : 0
      let maxRatio = 0
      for (let f = 0; f < nFaces; f++) {
        const ratio = dataArray[f] * invLimit
        if (ratio > maxRatio) maxRatio = ratio
      }
      if (maxRatio <= 0) maxRatio = 1
      const invMax = 1 / maxRatio

      for (let f = 0; f < nFaces; f++) {
        const t = dataArray[f] * invLimit * invMax
        const [r, g, b] = jetColor(t)
        const base = f * 9
        buf[base] = r; buf[base + 1] = g; buf[base + 2] = b
        buf[base + 3] = r; buf[base + 4] = g; buf[base + 5] = b
        buf[base + 6] = r; buf[base + 7] = g; buf[base + 8] = b
      }
    } else {
      const currentMax = arrayMax(dataArray)

      if (colormapLocked && colormapLockedMax == null) {
        useUIStore.getState().setColormapLockedMax(currentMax)
      }

      const maxSab = (colormapLocked && colormapLockedMax != null) ? colormapLockedMax : currentMax
      const nFaces = dataArray.length
      const invMax = maxSab > 0 ? 1 / maxSab : 0
      const isDb = legendScale === 'dB'

      for (let f = 0; f < nFaces; f++) {
        const t = isDb
          ? gainTFromLinear(dataArray[f], maxSab, dynamicRangeDb)
          : dataArray[f] * invMax
        const [r, g, b] = jetColor(t)
        const base = f * 9
        buf[base] = r; buf[base + 1] = g; buf[base + 2] = b
        buf[base + 3] = r; buf[base + 4] = g; buf[base + 5] = b
        buf[base + 6] = r; buf[base + 7] = g; buf[base + 8] = b
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
