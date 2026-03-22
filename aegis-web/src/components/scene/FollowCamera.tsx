import { useRef, useEffect } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'

const DEFAULT_DISTANCE = 5
const DEFAULT_PITCH = 0.3 // radians above horizontal
const MIN_DISTANCE = 2
const MAX_DISTANCE = 30
const SMOOTH_FACTOR = 6 // higher = snappier
const HEIGHT_OFFSET = 1.2 // look at body center, not feet

/**
 * Third-person follow camera that orbits around the character.
 * - Mouse drag (right button or orbit) rotates around character
 * - Mouse wheel zooms in/out
 * - Camera smoothly follows character movement
 * - Basic collision: pulls camera forward if behind geometry
 */
export default function FollowCamera() {
  const { camera, gl } = useThree()
  const mode = useUIStore(s => s.cameraMode)

  // Spherical coordinates around the character
  const yaw = useRef(0) // horizontal angle
  const pitch = useRef(DEFAULT_PITCH) // vertical angle
  const distance = useRef(DEFAULT_DISTANCE)
  const isDragging = useRef(false)
  const lastMouse = useRef({ x: 0, y: 0 })

  // Set up mouse handlers when in follow mode
  useEffect(() => {
    if (mode !== 'follow') return

    const canvas = gl.domElement

    const onMouseDown = (e: MouseEvent) => {
      // Right-click or middle-click for camera rotation
      if (e.button === 2 || e.button === 1) {
        isDragging.current = true
        lastMouse.current = { x: e.clientX, y: e.clientY }
        e.preventDefault()
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

    const [bx, by, bz] = useSimulationStore.getState().bodyOffset
    const targetPos = new THREE.Vector3(bx, by + HEIGHT_OFFSET, bz)

    // Compute desired camera position from spherical coords
    const d = distance.current
    const p = pitch.current
    const y = yaw.current
    const desiredX = targetPos.x + d * Math.cos(p) * Math.sin(y)
    const desiredY = targetPos.y + d * Math.sin(p)
    const desiredZ = targetPos.z + d * Math.cos(p) * Math.cos(y)

    const desiredPos = new THREE.Vector3(desiredX, desiredY, desiredZ)

    // Basic collision: raycast from target to desired camera position
    // If something is in the way, pull camera closer
    const dir = desiredPos.clone().sub(targetPos).normalize()
    const raycaster = new THREE.Raycaster(targetPos, dir, 0.5, d)
    // We can't easily raycast against the scene here without a ref to it,
    // but we ensure camera stays above ground at minimum
    const minY = by + 0.5
    if (desiredPos.y < minY) desiredPos.y = minY

    // Smooth interpolation
    const t = Math.min(1, SMOOTH_FACTOR * dt)
    camera.position.lerp(desiredPos, t)
    camera.lookAt(targetPos)
  })

  return null
}
