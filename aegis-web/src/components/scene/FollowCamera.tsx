import { useRef, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useKeyboard } from '@/hooks/useKeyboard'

const DEFAULT_DISTANCE = 5
const DEFAULT_PITCH = 0.3 // radians above horizontal
const MIN_DISTANCE = 2
const MAX_DISTANCE = 30
const SMOOTH_FACTOR = 6 // higher = snappier
const HEIGHT_OFFSET = 1.2 // look at body center, not feet
const ORBIT_SPEED = 2.0 // radians per second for Q/E keys

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

  const yaw = useRef(0)
  const pitch = useRef(DEFAULT_PITCH)
  const distance = useRef(DEFAULT_DISTANCE)
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
        MIN_DISTANCE,
        Math.min(MAX_DISTANCE, distance.current + e.deltaY * 0.01),
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
    if (keys.rotLeft) yaw.current += ORBIT_SPEED * dt
    if (keys.rotRight) yaw.current -= ORBIT_SPEED * dt

    const [bx, by, bz] = useSimulationStore.getState().bodyOffset
    const targetPos = new THREE.Vector3(bx, by + HEIGHT_OFFSET, bz)

    const d = distance.current
    const p = pitch.current
    const y = yaw.current
    const desiredX = targetPos.x + d * Math.cos(p) * Math.sin(y)
    const desiredY = targetPos.y + d * Math.sin(p)
    const desiredZ = targetPos.z + d * Math.cos(p) * Math.cos(y)

    const desiredPos = new THREE.Vector3(desiredX, desiredY, desiredZ)

    // Keep camera above ground
    const minY = by + 0.5
    if (desiredPos.y < minY) desiredPos.y = minY

    // Smooth interpolation
    const t = Math.min(1, SMOOTH_FACTOR * dt)
    camera.position.lerp(desiredPos, t)
    camera.lookAt(targetPos)
  })

  return null
}
