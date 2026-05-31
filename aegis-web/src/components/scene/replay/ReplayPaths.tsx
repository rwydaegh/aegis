import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import { toScene } from '@/api/coordinates'
import type { ReplayPath } from '@/api/replayTypes'

function orderColor(order: number): string {
  if (order === 0) return '#ffffff'
  if (order === 1) return '#ff8800'
  return '#ff3333'
}

export default function ReplayPaths({ paths }: { paths: ReplayPath[] }) {
  const lines = useMemo(() => {
    return paths
      .filter((p) => p.vertices.length >= 2)
      .map((p) => ({
        points: p.vertices.map((v) => toScene(v)),
        color: orderColor(p.order ?? 0),
      }))
  }, [paths])

  if (lines.length === 0) return null
  return (
    <group>
      {lines.map((l, i) => (
        <Line key={i} points={l.points} color={l.color} lineWidth={1.5} transparent opacity={0.8} />
      ))}
    </group>
  )
}
