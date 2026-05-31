import { useRef } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { useReplayStore } from '@/stores/replay'
import { toScene } from '@/api/coordinates'
import type { Vec3 } from '@/api/replayTypes'
import ReplaySceneGeometry from './ReplaySceneGeometry'
import ReplayArray from './ReplayArray'
import ReplayPaths from './ReplayPaths'
import ReplayBody from './ReplayBody'

function UEMarkers({ ues, active }: { ues: Vec3[]; active?: number }) {
  return (
    <group>
      {ues.map((u, i) => {
        const p = toScene(u)
        const isActive = i === active
        return (
          <mesh key={i} position={p}>
            <sphereGeometry args={[isActive ? 0.18 : 0.1, 12, 12]} />
            <meshStandardMaterial
              color={isActive ? '#22c55e' : '#64748b'}
              emissive={isActive ? '#16a34a' : '#000000'}
              emissiveIntensity={isActive ? 0.6 : 0}
            />
          </mesh>
        )
      })}
    </group>
  )
}

/** One-shot camera framing: look at the scene centre from a sensible offset. */
function ReplayCamera({ target }: { target: [number, number, number] }) {
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as { target: THREE.Vector3; update: () => void } | null
  const done = useRef(false)
  useFrame(() => {
    if (done.current || !controls) return
    done.current = true
    camera.position.set(target[0] + 18, target[1] + 16, target[2] + 28)
    controls.target.set(target[0], target[1], target[2])
    controls.update()
  })
  return null
}

export default function ReplayContent() {
  const artifact = useReplayStore((s) => s.artifact)
  const frameIndex = useReplayStore((s) => s.frameIndex)
  if (!artifact) return null
  const frame = artifact.frames[frameIndex]

  // Camera target: mean of UE positions, else room centre, else origin (scene coords).
  let target: [number, number, number] = [0, 1, 0]
  if (artifact.ues && artifact.ues.length > 0) {
    const m: Vec3 = [0, 0, 0]
    for (const u of artifact.ues) {
      m[0] += u[0]
      m[1] += u[1]
      m[2] += u[2]
    }
    const k = artifact.ues.length
    target = toScene([m[0] / k, m[1] / k, m[2] / k])
  } else if (artifact.scene.room?.center) {
    target = toScene(artifact.scene.room.center)
  }

  return (
    <>
      <color attach="background" args={['#0a0a0f']} />
      <ambientLight intensity={0.5} />
      <directionalLight position={[15, 25, 15]} intensity={0.8} castShadow />
      <hemisphereLight args={['#b1e1ff', '#2c2c2c', 0.4]} />

      <ReplaySceneGeometry scene={artifact.scene} />
      {artifact.array && <ReplayArray array={artifact.array} />}
      {artifact.body && <ReplayBody body={artifact.body} sab={frame?.sab} />}
      {artifact.ues && <UEMarkers ues={artifact.ues} active={frame?.ue_index} />}
      {frame?.paths && <ReplayPaths paths={frame.paths} />}

      <ReplayCamera target={target} />
      <OrbitControls makeDefault enableDamping />
    </>
  )
}
