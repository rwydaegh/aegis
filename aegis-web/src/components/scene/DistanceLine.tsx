import { useMemo, useEffect, useRef } from 'react'
import * as THREE from 'three'
import { Line } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { formatDistance } from '@/lib/format'

export default function DistanceLine() {
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const stats = useSimulationStore(s => s.stats)
  const config = useSceneStore(s => s.viewerConfig)

  const poleH = config?.antenna?.pole_height ?? 2
  const antennaTip: [number, number, number] | null = antennaPos
    ? [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]
    : null

  const bodyCenter: [number, number, number] = [bodyOffset[0], bodyOffset[1] + 0.6, bodyOffset[2]]

  const midpoint: [number, number, number] = antennaTip
    ? [
        (antennaTip[0] + bodyCenter[0]) / 2,
        (antennaTip[1] + bodyCenter[1]) / 2 + 0.2,
        (antennaTip[2] + bodyCenter[2]) / 2,
      ]
    : [0, 0, 0]

  const dist = stats?.distance_m
  const label = dist != null ? formatDistance(dist) : ''

  const prevTextureRef = useRef<THREE.CanvasTexture | null>(null)

  const labelTexture = useMemo(() => {
    // Dispose the previous texture to prevent GPU memory leaks
    prevTextureRef.current?.dispose()

    if (!label) {
      prevTextureRef.current = null
      return null
    }
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
    prevTextureRef.current = texture
    return texture
  }, [label])

  // Dispose texture on unmount
  useEffect(() => {
    return () => { prevTextureRef.current?.dispose() }
  }, [])

  if (!antennaTip) return null

  const points: [number, number, number][] = [
    antennaTip,
    bodyCenter,
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
