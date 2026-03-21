import { useMemo } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { formatDistance } from '@/lib/format'

export default function DistanceLine() {
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const stats = useSimulationStore(s => s.stats)

  const bodyCenter: [number, number, number] = [bodyOffset[0], bodyOffset[1] + 0.6, bodyOffset[2]]

  const midpoint: [number, number, number] = antennaPos
    ? [
        (antennaPos[0] + bodyCenter[0]) / 2,
        (antennaPos[1] + bodyCenter[1]) / 2 + 0.2,
        (antennaPos[2] + bodyCenter[2]) / 2,
      ]
    : [0, 0, 0]

  const dist = stats?.distance_m
  const label = dist != null ? formatDistance(dist) : ''

  const labelTexture = useMemo(() => {
    if (!label) return null
    const canvas = document.createElement('canvas')
    canvas.width = 128
    canvas.height = 32
    const ctx = canvas.getContext('2d')!
    ctx.fillStyle = 'rgba(0,0,0,0.6)'
    if (ctx.roundRect) {
      ctx.roundRect(0, 0, 128, 32, 4)
    } else {
      ctx.rect(0, 0, 128, 32)
    }
    ctx.fill()
    ctx.fillStyle = '#ffffff'
    ctx.font = 'bold 18px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(label, 64, 16)
    const texture = new THREE.CanvasTexture(canvas)
    return texture
  }, [label])

  if (!antennaPos) return null

  const points: [number, number, number][] = [
    [antennaPos[0], antennaPos[1], antennaPos[2]],
    [bodyCenter[0], bodyCenter[1], bodyCenter[2]],
  ]

  return (
    <group>
      <Line
        points={points}
        color="#ff6600"
        lineWidth={1.5}
        dashed
        dashSize={0.2}
        gapSize={0.1}
        transparent
        opacity={0.6}
      />
      {labelTexture && (
        <sprite position={midpoint} scale={[1, 0.25, 1]}>
          <spriteMaterial map={labelTexture} transparent />
        </sprite>
      )}
    </group>
  )
}
