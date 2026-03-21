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

  if (!rtPaths || rtPaths.length === 0) return null

  return (
    <group>
      {rtPaths.map((path, i) => {
        if (path.vertices.length < 2) return null

        const points: [number, number, number][] = path.vertices.map(v => {
          return toScene(v as [number, number, number])
        })

        return (
          <Line
            key={i}
            points={points}
            color={getColor(path.order)}
            lineWidth={1}
            transparent
            opacity={0.7}
          />
        )
      })}
    </group>
  )
}
