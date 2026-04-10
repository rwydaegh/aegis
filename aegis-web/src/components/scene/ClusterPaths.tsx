import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { toScene } from '@/api/coordinates'
import type { ClusterVizItem, SubpathVizItem } from '@/api/types'

// 12-color categorical palette (perceptually distinct, avoids pure red/green)
const CLUSTER_COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
  '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
  '#9c755f', '#bab0ac', '#d37295', '#a0cbe8',
]

const SCATTERER_RADIUS = 0.08
const SUBPATH_SCATTERER_RADIUS = 0.03

function ScattererSphere({ position, color, radius }: { position: [number, number, number]; color: string; radius?: number }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[radius ?? SCATTERER_RADIUS, 12, 8]} />
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
  const color = CLUSTER_COLORS[index % CLUSTER_COLORS.length]
  const opacity = Math.max(0.3, Math.min(1.0, cluster.power * 4))

  if (cluster.is_los) return null

  const fbs = cluster.fbs ? toScene(cluster.fbs) : antennaScene
  const lbs = cluster.lbs ? toScene(cluster.lbs) : bodyScene

  return (
    <group>
      <Line points={[antennaScene, fbs]} color={color} lineWidth={1.5} transparent opacity={opacity} />
      <Line points={[fbs, lbs]} color={color} lineWidth={1} transparent opacity={opacity * 0.5} dashed dashSize={0.15} gapSize={0.1} />
      <Line points={[lbs, bodyScene]} color={color} lineWidth={1.5} transparent opacity={opacity} />
      {cluster.fbs && <ScattererSphere position={fbs} color={color} />}
      {cluster.lbs && <ScattererSphere position={lbs} color={color} />}
    </group>
  )
}

function SubpathRay({ subpath, antennaScene, bodyScene }: {
  subpath: SubpathVizItem
  antennaScene: [number, number, number]
  bodyScene: [number, number, number]
}) {
  const color = CLUSTER_COLORS[subpath.cluster % CLUSTER_COLORS.length]
  const opacity = Math.max(0.15, Math.min(0.6, subpath.power * 8))

  if (subpath.is_los) return null

  const fbs = subpath.fbs ? toScene(subpath.fbs) : antennaScene
  const lbs = subpath.lbs ? toScene(subpath.lbs) : bodyScene

  return (
    <group>
      <Line points={[antennaScene, fbs]} color={color} lineWidth={0.5} transparent opacity={opacity * 0.4} />
      <Line points={[fbs, lbs]} color={color} lineWidth={0.5} transparent opacity={opacity * 0.3} dashed dashSize={0.1} gapSize={0.08} />
      <Line points={[lbs, bodyScene]} color={color} lineWidth={0.5} transparent opacity={opacity * 0.4} />
      {subpath.lbs && <ScattererSphere position={lbs} color={color} radius={SUBPATH_SCATTERER_RADIUS} />}
    </group>
  )
}

export default function ClusterPaths() {
  const clusterVizData = useSimulationStore(s => s.clusterVizData)
  const subpathVizData = useSimulationStore(s => s.subpathVizData)
  const clusterVizVisible = useSimulationStore(s => s.clusterVizVisible)
  const clusterVizDetail = useSimulationStore(s => s.clusterVizDetail)
  const pathSource = useSceneStore(s => s.pathSource)
  const antennaPos = useSimulationStore(s => s.antennaPos)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const config = useSceneStore(s => s.viewerConfig)

  const antennaScene = useMemo<[number, number, number] | null>(() => {
    if (!antennaPos || !config) return null
    const poleH = config.antenna?.pole_height ?? 2
    return [antennaPos[0], antennaPos[1] + poleH, antennaPos[2]]
  }, [antennaPos, config])

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

  const showSubpaths = clusterVizDetail === 'subpaths' && subpathVizData && subpathVizData.length > 0

  return (
    <group>
      {/* Always show cluster-level rays */}
      {clusterVizData.map((cluster, i) => (
        <ClusterRay
          key={`c-${i}`}
          cluster={cluster}
          index={i}
          antennaScene={antennaScene}
          bodyScene={bodyScene}
        />
      ))}
      {/* Optionally overlay sub-path rays */}
      {showSubpaths && subpathVizData.map((sp, i) => (
        <SubpathRay
          key={`s-${i}`}
          subpath={sp}
          antennaScene={antennaScene}
          bodyScene={bodyScene}
        />
      ))}
    </group>
  )
}
