import { useRef, useEffect } from 'react'
import * as THREE from 'three'
import type { ThreeEvent } from '@react-three/fiber'
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
  /** Click handler. Receives the R3F pointer event (with the world-space hit
   * point) so callers that need the surface coordinate, e.g. the studio's
   * pick-focus-on-body, can read `e.point`. Callers that ignore the arg keep
   * working unchanged. */
  onClick?: (e: ThreeEvent<MouseEvent>) => void
  // --- Optional colour-scale overrides ---
  // When provided, these take precedence over the shared useUIStore /
  // useSimulationStore reads, letting a standalone module (e.g. the Coherent
  // Exposure Studio) drive its own colour scale without cross-talk with the main
  // viewer. When omitted, the component falls back to the stores as before.
  displayQuantityOverride?: string
  legendScaleOverride?: string
  dynamicRangeDbOverride?: number
  colormapLockedOverride?: boolean
  colormapLockedMaxOverride?: number | null
  ratioModeOverride?: boolean
  /** Drive the wireframe toggle independently of the shared useUIStore (used by
   * the studio so its body-wireframe checkbox does not cross-talk with the main
   * viewer). When omitted, falls back to useUIStore.wireframe. */
  wireframeOverride?: boolean
  /** Colour ramp returning [r, g, b] in 0..1. Defaults to jetColor. */
  colorFn?: (t: number) => [number, number, number]
  /**
   * Render both faces of every triangle. Defaults to false (single-sided, the
   * main viewer's long-standing behaviour). The Coherent Exposure Studio sets
   * this true so the body never shows back-face culling holes regardless of
   * per-triangle winding.
   */
  doubleSided?: boolean
}

// ---------------------------------------------------------------------------
// Pure helpers (module scope)
// ---------------------------------------------------------------------------

function selectDataArray(
  displayQuantity: string,
  sabArray: Float32Array | null,
  sabAveragedArray?: Float32Array | null,
  sincArray?: Float32Array | null,
  sincAveragedArray?: Float32Array | null,
  sab1cm2AveragedArray?: Float32Array | null,
): Float32Array | null {
  const arrayMap: Record<string, Float32Array | null | undefined> = {
    sab: sabArray,
    sab_4cm2: sabAveragedArray,
    sab_1cm2: sab1cm2AveragedArray,
    sinc_local: sincArray,
    sinc_wb: sincAveragedArray,
  }
  return arrayMap[displayQuantity] ?? sabArray
}

function resolveRatioLimit(
  displayQuantity: string,
  compliance: ComplianceInfo | null | undefined,
): number {
  if (!compliance?.checks) return 1.0
  const limitMap: Record<string, (c: { label: string }) => boolean> = {
    sab_4cm2: (c) => c.label.includes('4 cm'),
    sab_1cm2: (c) => c.label.includes('1 cm'),
    sinc_local: (c) => c.label.includes('S_inc') && c.label.includes('local'),
    sinc_wb: (c) => c.label.includes('S_inc') && c.label.includes('whole-body'),
  }
  const finder = limitMap[displayQuantity]
  if (!finder) return 1.0
  return compliance.checks.find(finder)?.limit ?? 20.0
}

function writeRatioColors(
  buf: Float32Array,
  dataArray: Float32Array,
  ratioLimit: number,
  colorFn: (t: number) => [number, number, number] = jetColor,
): void {
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
    const [r, g, b] = colorFn(t)
    const base = f * 9
    buf[base] = r; buf[base + 1] = g; buf[base + 2] = b
    buf[base + 3] = r; buf[base + 4] = g; buf[base + 5] = b
    buf[base + 6] = r; buf[base + 7] = g; buf[base + 8] = b
  }
}

function writeAbsoluteColors(
  buf: Float32Array,
  dataArray: Float32Array,
  legendScale: string,
  dynamicRangeDb: number,
  colormapLocked: boolean,
  colormapLockedMax: number | null,
  colorFn: (t: number) => [number, number, number] = jetColor,
): void {
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
    const [r, g, b] = colorFn(t)
    const base = f * 9
    buf[base] = r; buf[base + 1] = g; buf[base + 2] = b
    buf[base + 3] = r; buf[base + 4] = g; buf[base + 5] = b
    buf[base + 6] = r; buf[base + 7] = g; buf[base + 8] = b
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

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
  displayQuantityOverride,
  legendScaleOverride,
  dynamicRangeDbOverride,
  colormapLockedOverride,
  colormapLockedMaxOverride,
  ratioModeOverride,
  wireframeOverride,
  colorFn,
  doubleSided = false,
}: BodyMeshInstanceProps) {
  const meshRef = useRef<THREE.Mesh>(null)

  // Always read the stores (hooks cannot be conditional), then let any provided
  // override win. Absent overrides fall back to the shared viewer state.
  const storeDisplayQuantity = useSimulationStore(s => s.displayQuantity)
  const storeWireframe = useUIStore(s => s.wireframe)
  const wireframe = wireframeOverride ?? storeWireframe
  const storeRatioMode = useUIStore(s => s.ratioMode)
  const storeLegendScale = useUIStore(s => s.legendScale)
  const storeDynamicRangeDb = useUIStore(s => s.dynamicRangeDb)
  const storeColormapLocked = useUIStore(s => s.colormapLocked)
  const storeColormapLockedMax = useUIStore(s => s.colormapLockedMax)

  const displayQuantity = displayQuantityOverride ?? storeDisplayQuantity
  const ratioMode = ratioModeOverride ?? storeRatioMode
  const legendScale = legendScaleOverride ?? storeLegendScale
  const dynamicRangeDb = dynamicRangeDbOverride ?? storeDynamicRangeDb
  const colormapLocked = colormapLockedOverride ?? storeColormapLocked
  const colormapLockedMax = colormapLockedMaxOverride ?? storeColormapLockedMax

  const dataArray = selectDataArray(
    displayQuantity, sabArray, sabAveragedArray, sincArray, sincAveragedArray, sab1cm2AveragedArray,
  )

  const isRatioMode = ratioMode && displayQuantity !== 'sab'
  const ratioLimit = isRatioMode ? resolveRatioLimit(displayQuantity, compliance) : 1.0

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
      writeRatioColors(buf, dataArray, ratioLimit, colorFn)
    } else {
      writeAbsoluteColors(buf, dataArray, legendScale, dynamicRangeDb, colormapLocked, colormapLockedMax, colorFn)
    }
    colorAttr.needsUpdate = true
  }, [dataArray, isRatioMode, ratioLimit, geometry, legendScale, dynamicRangeDb, colormapLocked, colormapLockedMax, colorFn])

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
          side={doubleSided ? THREE.DoubleSide : THREE.FrontSide}
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
