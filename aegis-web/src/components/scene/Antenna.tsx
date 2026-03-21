import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'

export default function Antenna() {
  const pos = useSimulationStore(s => s.antennaPos)
  const config = useSceneStore(s => s.viewerConfig)
  const wireframe = useUIStore(s => s.wireframe)

  if (!pos || !config) return null

  const ant = config.antenna
  const poleH = ant.pole_height ?? 2
  const poleR = ant.pole_radius ?? 0.015
  const sphereR = ant.sphere_radius ?? 0.08
  const coneRadius = ant.cone_radius ?? 0.05
  const coneH = ant.cone_height ?? 0.15

  return (
    <group position={pos}>
      {/* Pole: centered at half height */}
      <mesh position={[0, poleH / 2, 0]} castShadow>
        <cylinderGeometry args={[poleR, poleR, poleH, 8]} />
        <meshStandardMaterial color="#888888" wireframe={wireframe} />
      </mesh>
      {/* Hub sphere at top of pole */}
      <mesh position={[0, poleH, 0]}>
        <sphereGeometry args={[sphereR, 16, 16]} />
        <meshStandardMaterial color="#dddddd" wireframe={wireframe} />
      </mesh>
      {/* Cone pointing downward from hub */}
      <mesh position={[0, poleH - coneH / 2, 0]}>
        <coneGeometry args={[coneRadius, coneH, 16]} />
        <meshStandardMaterial color="#cccccc" wireframe={wireframe} />
      </mesh>
    </group>
  )
}
