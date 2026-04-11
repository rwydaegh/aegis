import { useMemo, useEffect, useRef, memo } from 'react'
import * as THREE from 'three'
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

// Reusable objects for instanced mesh updates (single-threaded, safe to share)
const _dummy = new THREE.Object3D()
const _color = new THREE.Color()

function ScattererSphere({ position, color, radius }: { position: [number, number, number]; color: string; radius?: number }) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[radius ?? SCATTERER_RADIUS, 12, 8]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.4} />
    </mesh>
  )
}

const ClusterRay = memo(function ClusterRay({ cluster, index, antennaScene, bodyScene }: {
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
})

/** All subpath line segments batched into a single draw call. */
function SubpathLines({ subpaths, antennaScene, bodyScene }: {
  subpaths: SubpathVizItem[]
  antennaScene: [number, number, number]
  bodyScene: [number, number, number]
}) {
  const geometry = useMemo(() => {
    const positions: number[] = []
    const colors: number[] = []

    for (const sp of subpaths) {
      if (sp.is_los) continue
      const c = _color.set(CLUSTER_COLORS[sp.cluster % CLUSTER_COLORS.length])
      const fbs = sp.fbs ? toScene(sp.fbs) : antennaScene
      const lbs = sp.lbs ? toScene(sp.lbs) : bodyScene

      // 3 line segments per subpath (antenna->fbs, fbs->lbs, lbs->body)
      positions.push(
        antennaScene[0], antennaScene[1], antennaScene[2], fbs[0], fbs[1], fbs[2],
        fbs[0], fbs[1], fbs[2], lbs[0], lbs[1], lbs[2],
        lbs[0], lbs[1], lbs[2], bodyScene[0], bodyScene[1], bodyScene[2],
      )
      colors.push(
        c.r, c.g, c.b, c.r, c.g, c.b,
        c.r, c.g, c.b, c.r, c.g, c.b,
        c.r, c.g, c.b, c.r, c.g, c.b,
      )
    }

    const geom = new THREE.BufferGeometry()
    geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
    geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    return geom
  }, [subpaths, antennaScene, bodyScene])

  useEffect(() => () => geometry.dispose(), [geometry])

  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial vertexColors transparent opacity={0.18} depthWrite={false} />
    </lineSegments>
  )
}

/** All subpath scatterer spheres batched into a single instanced draw call. */
function SubpathScatterers({ subpaths }: { subpaths: SubpathVizItem[] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null)

  const instances = useMemo(() => {
    const positions: [number, number, number][] = []
    const clusterIndices: number[] = []

    for (const sp of subpaths) {
      if (sp.is_los || !sp.lbs) continue
      positions.push(toScene(sp.lbs))
      clusterIndices.push(sp.cluster)
    }

    return { positions, clusterIndices, count: positions.length }
  }, [subpaths])

  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh || instances.count === 0) return

    for (let i = 0; i < instances.count; i++) {
      _dummy.position.set(...instances.positions[i])
      _dummy.updateMatrix()
      mesh.setMatrixAt(i, _dummy.matrix)
      mesh.setColorAt(i, _color.set(CLUSTER_COLORS[instances.clusterIndices[i] % CLUSTER_COLORS.length]))
    }
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [instances])

  if (instances.count === 0) return null

  return (
    <instancedMesh
      ref={meshRef}
      args={[null, null, instances.count] as unknown as [THREE.BufferGeometry, THREE.Material, number]}
      frustumCulled={false}
    >
      <sphereGeometry args={[SUBPATH_SCATTERER_RADIUS, 8, 6]} />
      <meshStandardMaterial toneMapped={false} />
    </instancedMesh>
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
      {clusterVizData.map((cluster, i) => (
        <ClusterRay
          key={`c-${i}`}
          cluster={cluster}
          index={i}
          antennaScene={antennaScene}
          bodyScene={bodyScene}
        />
      ))}
      {showSubpaths && subpathVizData && (
        <>
          <SubpathLines subpaths={subpathVizData} antennaScene={antennaScene} bodyScene={bodyScene} />
          <SubpathScatterers subpaths={subpathVizData} />
        </>
      )}
    </group>
  )
}
