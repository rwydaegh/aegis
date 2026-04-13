import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import { useSceneStore } from '@/stores/scene'
import { toScene } from '@/api/coordinates'

function getColor(order: number): string {
  if (order === 0) return '#ffffff'
  if (order === 1) return '#ff6600'
  return '#ff0000'
}

export default function RayPaths() {
  const rtPaths = useSceneStore(s => s.rtPaths)

  const processedPaths = useMemo(() => {
    if (!rtPaths || rtPaths.length === 0) return null
    return rtPaths
      .filter(path => path.vertices.length >= 2)
      .map(path => ({
        points: path.vertices.map(v => toScene(v as [number, number, number])),
        color: getColor(path.order),
      }))
  }, [rtPaths])

  if (!processedPaths || processedPaths.length === 0) return null

  return (
    <group>
      {processedPaths.map((path, i) => (
        <Line
          key={i}
          points={path.points}
          color={path.color}
          lineWidth={1}
          transparent
          opacity={0.7}
        />
      ))}
    </group>
  )
}
