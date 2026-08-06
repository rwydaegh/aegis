import { useLayoutEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { toScene } from '@/api/coordinates'
import { useStudioStore } from '../store'
import { colormapRgb, rayHeadScale, rayOpacity, rayPowerToColorT, rayWidth } from './studioHelpers'
import type { RaysResponse } from '../api'

const MAX_RAYS = 150
// Visible ray length, drawn OUTWARD from the cutoff radius [m]. The inner end
// sits at the ray cutoff radius (rayCutoffM) so the rays stop short of the
// focus instead of piling onto the hotspot and hiding it.
const SEGMENT_LEN = 1.8
// Power dynamic range spread across the colormap (dB below the strongest path).
const RAY_RANGE_DB = 40
// Base arrowhead cone at the inner (focus-side) end of each ray, scaled per ray
// by power so a strong arrival carries a clearly bigger head than a faint one.
// Kept small and many-sided so the cone reads as a smooth dart, not a block.
const HEAD_RADIUS = 0.013
const HEAD_HEIGHT = 0.05
const HEAD_SEGMENTS = 24
const CONE_AXIS = new THREE.Vector3(0, 1, 0)
// Neutral ray tint for the 'mono' colour mode, chosen per background so the
// rays stay legible on both the dark working view and the white figure view.
const MONO_RGB_DARK: [number, number, number] = [196, 220, 255]
const MONO_RGB_LIGHT: [number, number, number] = [40, 64, 110]

interface StudioRaysProps {
  rays: RaysResponse | null
}

// Top arrival directions drawn as short arrows pointing in toward the focus
// (downlink onto the body). Each ray is a fixed-length segment whose inner end
// stops at the ray cutoff radius (rayCutoffM, an independent slider) so it never
// reaches the focus and occludes the hotspot. Per-ray power drives line WIDTH
// (bold = strong), OPACITY (faint paths recede) and arrowhead SIZE, plus COLOUR
// through the studio colormap on a dB scale unless the mono mode is on.
export default function StudioRays({ rays }: StudioRaysProps) {
  const focusXyz = useStudioStore((s) => s.focusXyz)
  const cutoffM = useStudioStore((s) => s.rayCutoffM)
  const colormap = useStudioStore((s) => s.colormap)
  const thickness = useStudioStore((s) => s.rayThickness)
  const colorMode = useStudioStore((s) => s.rayColorMode)
  const background = useStudioStore((s) => s.background)
  const headsRef = useRef<THREE.InstancedMesh>(null)

  const segments = useMemo(() => {
    if (!rays || rays.directions.length === 0) return []
    const n = Math.min(rays.directions.length, MAX_RAYS)
    let pMax = 0
    for (let i = 0; i < n; i++) pMax = Math.max(pMax, rays.power[i] ?? 0)
    if (pMax <= 0) pMax = 1

    const focusScene = toScene(focusXyz)
    const inner = Math.max(cutoffM, 0)
    const outer = inner + SEGMENT_LEN
    const mono = colorMode === 'mono' ? (background === 'white' ? MONO_RGB_LIGHT : MONO_RGB_DARK) : null

    const out: {
      points: [number, number, number][]
      end: [number, number, number]
      dir: [number, number, number]
      color: string
      rgb: [number, number, number]
      width: number
      opacity: number
      scale: number
    }[] = []
    for (let i = 0; i < n; i++) {
      const dir = toScene(rays.directions[i]) // unit propagation dir, toward focus
      const t = rayPowerToColorT(rays.power[i] ?? 0, pMax, RAY_RANGE_DB)
      const [r, g, b] = mono ?? colormapRgb(colormap, t)
      const start: [number, number, number] = [
        focusScene[0] - dir[0] * outer,
        focusScene[1] - dir[1] * outer,
        focusScene[2] - dir[2] * outer,
      ]
      const end: [number, number, number] = [
        focusScene[0] - dir[0] * inner,
        focusScene[1] - dir[1] * inner,
        focusScene[2] - dir[2] * inner,
      ]
      out.push({
        points: [start, end],
        end,
        dir: [dir[0], dir[1], dir[2]],
        color: `rgb(${r},${g},${b})`,
        rgb: [r, g, b],
        width: rayWidth(t, thickness),
        opacity: rayOpacity(t),
        scale: rayHeadScale(t),
      })
    }
    return out
  }, [rays, focusXyz, cutoffM, colormap, thickness, colorMode, background])

  // Place + orient + colour + size the arrowhead cones (one instance per ray).
  useLayoutEffect(() => {
    const mesh = headsRef.current
    if (!mesh) return
    const m = new THREE.Matrix4()
    const q = new THREE.Quaternion()
    const pos = new THREE.Vector3()
    const dirV = new THREE.Vector3()
    const scl = new THREE.Vector3()
    const col = new THREE.Color()
    segments.forEach((seg, i) => {
      dirV.set(seg.dir[0], seg.dir[1], seg.dir[2]).normalize()
      q.setFromUnitVectors(CONE_AXIS, dirV) // cone apex (+Y) -> arrival dir (toward focus)
      pos.set(seg.end[0], seg.end[1], seg.end[2])
      scl.set(seg.scale, seg.scale, seg.scale)
      m.compose(pos, q, scl)
      mesh.setMatrixAt(i, m)
      col.setRGB(seg.rgb[0] / 255, seg.rgb[1] / 255, seg.rgb[2] / 255)
      mesh.setColorAt(i, col)
    })
    mesh.count = segments.length
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [segments])

  if (segments.length === 0) return null

  return (
    <group>
      {segments.map((seg, i) => (
        <Line key={i} points={seg.points} color={seg.color} lineWidth={seg.width} transparent opacity={seg.opacity} />
      ))}
      <instancedMesh ref={headsRef} args={[undefined, undefined, MAX_RAYS]}>
        <coneGeometry args={[HEAD_RADIUS, HEAD_HEIGHT, HEAD_SEGMENTS]} />
        <meshBasicMaterial toneMapped={false} />
      </instancedMesh>
    </group>
  )
}
