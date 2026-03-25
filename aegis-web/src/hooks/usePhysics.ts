import { useRef, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { stepPhysics, type PhysicsState, type PhysicsConfig } from '@/lib/physics'
import { useKeyboard } from './useKeyboard'
import { useMIMOStore } from '@/stores/mimo'

export function usePhysics() {
  const keys = useKeyboard()
  const { camera } = useThree()

  const initialOffset = useSimulationStore(s => s.bodyOffset)
  const physicsState = useRef<PhysicsState>({
    position: [...initialOffset],
    velocity: [0, 0, 0],
    rotationY: 0,
    angularVelocity: 0,
    onGround: false,  // start false so first frame runs ground-snap
  })

  const controlledUserId = useMIMOStore(s => s.controlledUserId)

  useEffect(() => {
    if (!controlledUserId) return
    const user = useMIMOStore.getState().users.get(controlledUserId)
    if (user) {
      physicsState.current = {
        position: [...user.position],
        velocity: [0, 0, 0],
        rotationY: user.orientation,
        angularVelocity: 0,
        onGround: false,  // let first frame ground-snap to correct height
      }
    }
  }, [controlledUserId])

  useFrame((_, dt) => {
    const config = useSceneStore.getState().viewerConfig
    if (!config) return

    const heightmapFn = useSceneStore.getState().voxelHeightmap
    const getGroundY = heightmapFn ?? ((_x: number, _z: number, _y: number) => 0)

    // Get camera forward direction (flattened to XZ)
    const camDir = new THREE.Vector3()
    camera.getWorldDirection(camDir)
    const cameraDirection: [number, number] = [camDir.x, camDir.z]
    const len = Math.sqrt(cameraDirection[0] ** 2 + cameraDirection[1] ** 2)
    if (len > 0.001) {
      cameraDirection[0] /= len
      cameraDirection[1] /= len
    }

    const hasInput =
      keys.forward ||
      keys.back ||
      keys.left ||
      keys.right ||
      keys.rotLeft ||
      keys.rotRight ||
      keys.jump

    const isMoving =
      Math.abs(physicsState.current.velocity[0]) > 0.01 ||
      Math.abs(physicsState.current.velocity[2]) > 0.01 ||
      Math.abs(physicsState.current.angularVelocity) > 0.01

    if (!hasInput && !isMoving && physicsState.current.onGround) return

    const physicsConfig = config.physics as PhysicsConfig

    const newState = stepPhysics(
      physicsState.current,
      keys,
      cameraDirection,
      getGroundY,
      physicsConfig,
      dt,
    )

    physicsState.current = newState

    // Write to MIMO store or simulation store depending on mode
    const mimoStore = useMIMOStore.getState()
    if (mimoStore.enabled && mimoStore.controlledUserId) {
      const user = mimoStore.users.get(mimoStore.controlledUserId)
      if (user) {
        const [px, py, pz] = newState.position
        const [ox, oy, oz] = user.position
        if (px !== ox || py !== oy || pz !== oz) {
          mimoStore.moveUser(mimoStore.controlledUserId, newState.position)
        }
        if (newState.rotationY !== user.orientation) {
          mimoStore.setUserOrientation(mimoStore.controlledUserId, newState.rotationY)
        }
      }
    } else {
      const simStore = useSimulationStore.getState()
      const [px, py, pz] = newState.position
      const [ox, oy, oz] = simStore.bodyOffset
      if (px !== ox || py !== oy || pz !== oz) {
        simStore.setBodyOffset(newState.position)
      }
      if (newState.rotationY !== simStore.bodyRotationY) {
        simStore.setBodyRotationY(newState.rotationY)
      }
    }
  })
}
