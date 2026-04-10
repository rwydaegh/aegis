import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { toScene } from '@/api/coordinates'
import type { ClusterVizItem } from '@/api/types'

// 12-color categorical palette (perceptually distinct, avoids pure red/green)
const CLUSTER_COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
  '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
  '#9c755f', '#bab0ac', '#d37295', '#a0cbe8',
]

const SCATTERER_RADIUS = 0.08
const LOS_COLOR = '#ffffff'

function ScattererSphere({ position, color }: { position: [number, number, number]; color: string }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[SCATTERER_RADIUS, 12, 8]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
    </mesh>
  )
}

function ClusterRay({ cluster, index, antennaScene, bodyScene }: {
  cluster: ClusterVizItem
  index: number
  antennaScene: [number, number, number]
  bodyScene: [number, number, number]
}) {
  const color = cluster.is_los ? LOS_COLOR : CLUSTER_COLORS[index % CLUSTER_COLORS.length]
  const opacity = Math.max(0.3, Math.min(1.0, cluster.power * 4))

  if (cluster.is_los) {
    // LOS: single line from antenna to body
    return (
      <Line
        points={[antennaScene, bodyScene]}
        color={color}
        lineWidth={2.5}
        transparent
        opacity={opacity}
      />
    )
  }

  // NLOS: antenna -> FBS, FBS -> LBS (dashed), LBS -> body
  const fbs = cluster.fbs ? toScene(cluster.fbs) : antennaScene
  const lbs = cluster.lbs ? toScene(cluster.lbs) : bodyScene

  return (
    <group>
      {/* Antenna -> FBS */}
      <Line
        points={[antennaScene, fbs]}
        color={color}
        lineWidth={1.5}
        transparent
        opacity={opacity}
      />
      {/* FBS -> LBS (dashed) */}
      <Line
        points={[fbs, lbs]}
        color={color}
        lineWidth={1}
        transparent
        opacity={opacity * 0.5}
        dashed
        dashSize={0.15}
        gapSize={0.1}
      />
      {/* LBS -> Body */}
      <Line
        points={[lbs, bodyScene]}
        color={color}
        lineWidth={1.5}
        transparent
        opacity={opacity}
      />
      {/* Scatterer markers */}
      {cluster.fbs && <ScattererSphere position={fbs} color={color} />}
      {cluster.lbs && <ScattererSphere position={lbs} color={color} />}
    </group>
  )
}

export default function ClusterPaths() {
  const clusterVizData = useSimulationStore(s => s.clusterVizData)
  const clusterVizVisible = useSimulationStore(s => s.clusterVizVisible)
  const pathSource = useSceneStore(s => s.pathSource)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const config = useSceneStore(s => s.viewerConfig)

  const antennaScene = useMemo<[number, number, number] | null>(() => {
    if (!antennaPos || !config) return null
    const poleH = config.antenna?.pole_height ?? 2
    return [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]
  }, [antennaPos, config])

  // Body center approximation (body feet + half height)
  const bodyScene = useMemo<[number, number, number]>(() => {
    return [bodyOffset[0], bodyOffset[1] + 0.6, bodyOffset[2]]
  }, [bodyOffset])

  if (
    !clusterVizVisible ||
    !clusterVizData ||
    clusterVizData.length === 0 ||
    pathSource !== 'stochastic' ||
    !antennaScene
  ) {
    return null
  }

  return (
    <group>
      {clusterVizData.map((cluster, i) => (
        <ClusterRay
          key={i}
          cluster={cluster}
          index={i}
          antennaScene={antennaScene}
          bodyScene={bodyScene}
        />
      ))}
    </group>
  )
}
