import { useRef } from 'react'
import { useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { useReplayStore } from '@/stores/replay'
import { toScene } from '@/api/coordinates'
import type { Vec3, ReplayBox } from '@/api/replayTypes'
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

/**
 * Camera framing: follow the served body. Re-frames whenever the active UE
 * changes (scrubbing across UEs tracks the person), centred on the body's
 * mid-height with an offset that keeps the body, its incident rays and the
 * base-station array in view.
 */
function ReplayCamera({ target, ueKey }: { target: [number, number, number]; ueKey: number }) {
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as { target: THREE.Vector3; update: () => void } | null
  const lastKey = useRef<number | null>(null)
  useFrame(() => {
    if (!controls || lastKey.current === ueKey) return
    lastKey.current = ueKey
    camera.position.set(target[0] + 8, target[1] + 5.5, target[2] + 11)
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

  // Active-frame scene boxes: the frame's realization scatterers (or the shared
  // scene.boxes for single-realization artifacts), plus the blocker when NLOS.
  const realizationBoxes =
    artifact.realizations && frame?.realization != null
      ? artifact.realizations[frame.realization]?.boxes ?? []
      : artifact.scene.boxes ?? []
  const showBlocker = !!artifact.scene.blocker && /nlos/i.test(frame?.condition ?? '')
  const boxes: ReplayBox[] = showBlocker
    ? [...realizationBoxes, artifact.scene.blocker as ReplayBox]
    : realizationBoxes

  // Camera target: the served body's mid-height (scene coords). Falls back to
  // the mean UE, then the room centre.
  let target: [number, number, number] = [0, 1, 0]
  if (frame?.body_pos) {
    const s = toScene(frame.body_pos)
    target = [s[0], s[1] + 0.95, s[2]]
  } else if (artifact.ues && artifact.ues.length > 0) {
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

      <ReplaySceneGeometry scene={artifact.scene} boxes={boxes} />
      {artifact.array && <ReplayArray array={artifact.array} />}
      {artifact.body && <ReplayBody body={artifact.body} sab={frame?.sab} bodyPos={frame?.body_pos} />}
      {artifact.ues && <UEMarkers ues={artifact.ues} active={frame?.ue_index} />}
      {frame?.paths && <ReplayPaths paths={frame.paths} />}

      <ReplayCamera target={target} ueKey={frame?.ue_index ?? 0} />
      <OrbitControls makeDefault enableDamping />
    </>
  )
}
