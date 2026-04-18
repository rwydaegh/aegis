import { useRef, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { useUIStore } from '@/stores/ui'
import { useSceneStore } from '@/stores/scene'
import { useKeyboard } from '@/hooks/useKeyboard'

const FALLBACK_FOLLOW = {
  default_distance: 5,
  default_pitch: 0.3,
  min_distance: 2,
  max_distance: 30,
  smooth_factor: 6,
  height_offset: 1.2,
  orbit_speed: 2.0,
}

/**
 * Third-person follow camera that orbits around the character.
 * - Q/E keys orbit camera around character
 * - Left-click drag orbits camera around character
 * - Mouse wheel zooms in/out
 * - Camera smoothly follows character movement
 */
export default function FollowCamera() {
  const { camera, gl } = useThree()
  const mode = useUIStore(s => s.cameraMode)
  const keys = useKeyboard()
  const followCfg = useSceneStore(s => s.viewerConfig?.camera?.follow) ?? FALLBACK_FOLLOW

  const yaw = useRef(0)
  const pitch = useRef(followCfg.default_pitch)
  // Reusable Vector3 objects to avoid per-frame GC pressure
  const _targetPos = useRef(new THREE.Vector3())
  const _desiredPos = useRef(new THREE.Vector3())
  const distance = useRef(followCfg.default_distance)
  const isDragging = useRef(false)
  const lastMouse = useRef({ x: 0, y: 0 })

  useEffect(() => {
    if (mode !== 'follow') return

    const canvas = gl.domElement

    const onMouseDown = (e: MouseEvent) => {
      // Left-click or right-click for camera orbit
      if (e.button === 0 || e.button === 2) {
        isDragging.current = true
        lastMouse.current = { x: e.clientX, y: e.clientY }
      }
    }

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return
      const dx = e.clientX - lastMouse.current.x
      const dy = e.clientY - lastMouse.current.y
      lastMouse.current = { x: e.clientX, y: e.clientY }

      yaw.current -= dx * 0.005
      pitch.current = Math.max(-0.2, Math.min(Math.PI / 2 - 0.1, pitch.current + dy * 0.005))
    }

    const onMouseUp = () => {
      isDragging.current = false
    }

    const onWheel = (e: WheelEvent) => {
      distance.current = Math.max(
        followCfg.min_distance,
        Math.min(followCfg.max_distance, distance.current + e.deltaY * 0.01),
      )
      e.preventDefault()
    }

    const onContextMenu = (e: Event) => e.preventDefault()

    canvas.addEventListener('mousedown', onMouseDown)
    canvas.addEventListener('mousemove', onMouseMove)
    canvas.addEventListener('mouseup', onMouseUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    canvas.addEventListener('contextmenu', onContextMenu)

    return () => {
      canvas.removeEventListener('mousedown', onMouseDown)
      canvas.removeEventListener('mousemove', onMouseMove)
      canvas.removeEventListener('mouseup', onMouseUp)
      canvas.removeEventListener('wheel', onWheel)
      canvas.removeEventListener('contextmenu', onContextMenu)
    }
  }, [mode, gl])

  useFrame((_, dt) => {
    if (mode !== 'follow') return

    // Q/E keys orbit the camera around the character
    if (keys.rotLeft) yaw.current += followCfg.orbit_speed * dt
    if (keys.rotRight) yaw.current -= followCfg.orbit_speed * dt

    // In MIMO mode, follow the controlled user's position
    const mimoState = useMIMOStore.getState()
    let bodyPos: [number, number, number]
    if (mimoState.enabled && mimoState.controlledUserId) {
      const user = mimoState.users.get(mimoState.controlledUserId)
      bodyPos = user?.position ?? useSimulationStore.getState().bodyOffset
    } else {
      bodyPos = useSimulationStore.getState().bodyOffset
    }
    const [bx, by, bz] = bodyPos
    const targetPos = _targetPos.current.set(bx, by + followCfg.height_offset, bz)

    const d = distance.current
    const p = pitch.current
    const y = yaw.current
    const desiredPos = _desiredPos.current.set(
      targetPos.x + d * Math.cos(p) * Math.sin(y),
      targetPos.y + d * Math.sin(p),
      targetPos.z + d * Math.cos(p) * Math.cos(y),
    )

    // Keep camera above ground
    const minY = by + 0.5
    if (desiredPos.y < minY) desiredPos.y = minY

    // Smooth interpolation
    const t = Math.min(1, followCfg.smooth_factor * dt)
    camera.position.lerp(desiredPos, t)
    camera.lookAt(targetPos)
  })

  return null
}
