import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import { useOptimizeStore } from '@/stores/optimize'
import { useSimulationStore } from '@/stores/simulation'

const DOT_RADIUS = 0.12
const COLOR_PREVIEW = '#4a9eff'
const COLOR_EVALUATED = '#94a3b8'
const COLOR_BEST = '#22c55e'
const COLOR_CURRENT = '#fbbf24'

export default function OptimizeGridPreview() {
  const mode = useOptimizeStore(s => s.mode)
  const running = useOptimizeStore(s => s.running)
  const constraints = useOptimizeStore(s => s.constraints)
  const currentIter = useOptimizeStore(s => s.currentIter)
  const history = useOptimizeStore(s => s.history)
  const summary = useOptimizeStore(s => s.summary)
  const placementCenter = useOptimizeStore(s => s.placementCenter)
  const antennaPos = useSimulationStore(s => s.antennaPos)

  // Use frozen center during/after optimization, live antenna pos for preview
  const center = (running || summary) ? placementCenter : antennaPos

  const gridSize = constraints.gridSize ?? 5
  const gridSpacing = constraints.gridSpacing ?? 2.0

  // Compute grid points in scene coordinates
  // Backend free_axes=(0,2): varies server X (=scene X) and server Z (=scene Y)
  const gridPoints = useMemo(() => {
    if (!center) return []
    const half = (gridSize - 1) / 2
    const points: [number, number, number][] = []
    for (let a = 0; a < gridSize; a++) {
      for (let b = 0; b < gridSize; b++) {
        points.push([
          center[0] + (a - half) * gridSpacing,
          center[1] + (b - half) * gridSpacing,
          center[2],
        ])
      }
    }
    return points
  }, [center?.[0], center?.[1], center?.[2], gridSize, gridSpacing])

  // Grid lines: horizontal (along X) and vertical (along Y)
  const gridLines = useMemo(() => {
    if (!center) return []
    const half = (gridSize - 1) / 2
    const result: [number, number, number][][] = []
    for (let row = 0; row < gridSize; row++) {
      const yOff = (row - half) * gridSpacing
      const pts: [number, number, number][] = []
      for (let col = 0; col < gridSize; col++) {
        pts.push([center[0] + (col - half) * gridSpacing, center[1] + yOff, center[2]])
      }
      result.push(pts)
    }
    for (let col = 0; col < gridSize; col++) {
      const xOff = (col - half) * gridSpacing
      const pts: [number, number, number][] = []
      for (let row = 0; row < gridSize; row++) {
        pts.push([center[0] + xOff, center[1] + (row - half) * gridSpacing, center[2]])
      }
      result.push(pts)
    }
    return result
  }, [center?.[0], center?.[1], center?.[2], gridSize, gridSpacing])

  // Find the best grid point index from history
  const bestIdx = useMemo(() => {
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i].isBest) return i
    }
    return -1
  }, [history])

  if (mode !== 'placement' || !center) return null

  const hasResults = running || (summary !== null && history.length > 0)
  const evaluatedCount = hasResults ? (running ? currentIter : history.length) : 0

  return (
    <group>
      {gridLines.map((pts, i) => (
        <Line
          key={`grid-line-${i}`}
          points={pts}
          color={COLOR_PREVIEW}
          lineWidth={1}
          transparent
          opacity={hasResults ? 0.08 : 0.15}
        />
      ))}
      {gridPoints.map((pt, i) => {
        let color = COLOR_PREVIEW
        let opacity = 0.4
        let scale = 1

        if (hasResults) {
          if (i < evaluatedCount) {
            if (i === bestIdx) {
              color = COLOR_BEST
              opacity = 0.9
              scale = 1.6
            } else {
              color = COLOR_EVALUATED
              opacity = 0.5
              scale = 0.8
            }
          } else if (running && i === evaluatedCount) {
            color = COLOR_CURRENT
            opacity = 0.9
            scale = 1.3
          } else {
            opacity = 0.2
            scale = 0.7
          }
        }

        return (
          <mesh key={i} position={pt} scale={scale}>
            <sphereGeometry args={[DOT_RADIUS, 8, 6]} />
            <meshBasicMaterial
              color={color}
              transparent
              opacity={opacity}
              depthWrite={false}
            />
          </mesh>
        )
      })}
    </group>
  )
}
