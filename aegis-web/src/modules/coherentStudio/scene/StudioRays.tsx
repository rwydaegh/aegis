import { useMemo } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { toScene } from '@/api/coordinates'
import { useStudioStore } from '../store'
import type { RaysResponse } from '../api'

const MAX_RAYS = 150
const RAY_LENGTH = 1.2
const COOL = new THREE.Color('#3a7bd5')
const WARM = new THREE.Color('#ff5a36')

interface StudioRaysProps {
  rays: RaysResponse | null
}

// Top arrival directions drawn as lines converging on the focus (downlink onto
// the body). Each ray starts offset along -direction and arrives at the focus;
// normalised power drives both line WIDTH (fat = strong) and a warm-cool COLOUR.
export default function StudioRays({ rays }: StudioRaysProps) {
  const focusXyz = useStudioStore((s) => s.focusXyz)

  const segments = useMemo(() => {
    if (!rays || rays.directions.length === 0) return []
    const n = Math.min(rays.directions.length, MAX_RAYS)
    let pMax = 0
    for (let i = 0; i < n; i++) pMax = Math.max(pMax, rays.power[i] ?? 0)
    if (pMax <= 0) pMax = 1

    const focusScene = toScene(focusXyz)
    const out: { points: [number, number, number][]; color: string; width: number }[] = []
    for (let i = 0; i < n; i++) {
      const dir = toScene(rays.directions[i])
      const start: [number, number, number] = [
        focusScene[0] - dir[0] * RAY_LENGTH,
        focusScene[1] - dir[1] * RAY_LENGTH,
        focusScene[2] - dir[2] * RAY_LENGTH,
      ]
      const t = Math.min(1, Math.max(0, (rays.power[i] ?? 0) / pMax))
      const color = COOL.clone().lerp(WARM, t).getStyle()
      const width = 1 + 5 * t
      out.push({ points: [start, focusScene], color, width })
    }
    return out
  }, [rays, focusXyz])

  if (segments.length === 0) return null

  return (
    <group>
      {segments.map((seg, i) => (
        <Line
          key={i}
          points={seg.points}
          color={seg.color}
          lineWidth={seg.width}
          transparent
          opacity={0.75}
        />
      ))}
    </group>
  )
}
