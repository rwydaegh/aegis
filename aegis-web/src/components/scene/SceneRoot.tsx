import { useRef } from 'react'
import { Canvas, useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useDosimetry } from '@/hooks/useDosimetry'
import { usePhysics } from '@/hooks/usePhysics'
import BodyMesh from './BodyMesh'
import Antenna from './Antenna'
import DistanceLine from './DistanceLine'
import RayPaths from './RayPaths'
import VoxelField from './VoxelField'
import SceneGeometry from './SceneGeometry'
import Environment from './Environment'

// Body is roughly 1.2 m tall, centered at origin, feet at y=0
const BODY_TARGET = new THREE.Vector3(0, 0.6, 0)
const BODY_RADIUS = 1.0 // rough half-height for focus zoom

const PRESET_CAMERA: Record<string, { position: [number, number, number]; target: [number, number, number] }> = {
  front: { position: [0, 1, 4], target: [0, 0.6, 0] },
  side:  { position: [4, 1, 0], target: [0, 0.6, 0] },
  top:   { position: [0, 6, 0.01], target: [0, 0, 0] },
  focus: { position: [0, 0.6, 2.5], target: [0, 0.6, 0] },
}

/**
 * Listens to ui.cameraPreset and smoothly transitions the camera + orbit target.
 * Must live inside the R3F Canvas so it can access useThree.
 */
function CameraController({ controlsRef, initialPosition }: {
  controlsRef: React.RefObject<OrbitControlsImpl | null>
  initialPosition: [number, number, number]
}) {
  const { camera } = useThree()
  const preset = useUIStore(s => s.cameraPreset)

  // Animation state
  const animating = useRef(false)
  const fromPos = useRef(new THREE.Vector3())
  const toPos = useRef(new THREE.Vector3())
  const fromTarget = useRef(new THREE.Vector3())
  const toTarget = useRef(new THREE.Vector3())
  const progress = useRef(0)
  const DURATION = 0.5 // seconds

  // When preset changes, start animation
  const lastPreset = useRef<string | null>(null)
  if (preset && preset !== lastPreset.current) {
    lastPreset.current = preset

    const controls = controlsRef.current
    fromPos.current.copy(camera.position)
    fromTarget.current.copy(controls ? (controls.target as THREE.Vector3) : BODY_TARGET)

    let dest: { position: [number, number, number]; target: [number, number, number] }
    if (preset === 'reset') {
      dest = { position: initialPosition, target: [0, 0.6, 0] }
    } else {
      dest = PRESET_CAMERA[preset] ?? PRESET_CAMERA.front
    }

    toPos.current.set(...dest.position)
    toTarget.current.set(...dest.target)
    progress.current = 0
    animating.current = true
  }

  useFrame((_, delta) => {
    if (!animating.current) return
    const controls = controlsRef.current
    progress.current = Math.min(1, progress.current + delta / DURATION)
    // Smooth step easing
    const t = progress.current * progress.current * (3 - 2 * progress.current)

    camera.position.lerpVectors(fromPos.current, toPos.current, t)

    if (controls) {
      const target = controls.target as THREE.Vector3
      target.lerpVectors(fromTarget.current, toTarget.current, t)
      controls.update()
    }

    if (progress.current >= 1) {
      animating.current = false
    }
  })

  return null
}

function SceneLighting() {
  const config = useSceneStore(s => s.viewerConfig)
  if (!config) return null
  const light = config.lighting as any

  return (
    <>
      <ambientLight intensity={light?.ambient?.intensity ?? 0.4} color={light?.ambient?.color ?? '#ffffff'} />
      <directionalLight
        position={light?.sun?.position ?? [5, 10, 5]}
        intensity={light?.sun?.intensity ?? 0.8}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      {light?.fill && (
        <directionalLight
          position={light.fill.position ?? [-3, 5, -5]}
          intensity={light.fill.intensity ?? 0.3}
        />
      )}
      <hemisphereLight
        args={[light?.hemisphere?.sky_color ?? '#b1e1ff', light?.hemisphere?.ground_color ?? '#2c2c2c', light?.hemisphere?.intensity ?? 0.3]}
      />
    </>
  )
}

function Ground() {
  const config = useSceneStore(s => s.viewerConfig)
  const gp = (config?.scene?.ground_plane ?? {}) as any
  if (gp.visible === false) return null

  const pointerDownPos = useRef<{ x: number; y: number } | null>(null)

  const handlePointerDown = (e: ThreeEvent<PointerEvent>) => {
    pointerDownPos.current = { x: e.clientX, y: e.clientY }
  }

  const handlePointerUp = (e: ThreeEvent<PointerEvent>) => {
    if (!pointerDownPos.current || !config) return
    const dx = e.clientX - pointerDownPos.current.x
    const dy = e.clientY - pointerDownPos.current.y
    const dist = Math.sqrt(dx * dx + dy * dy)
    const threshold = config.interaction.click_max_drag_px ?? 5

    if (dist <= threshold && e.intersections.length > 0) {
      const point = e.intersections[0].point
      useSimulationStore.getState().setAntennaPos([point.x, point.y, point.z])
    }
    pointerDownPos.current = null
  }

  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, gp.y ?? 0, 0]}
      receiveShadow
      onPointerDown={handlePointerDown}
      onPointerUp={handlePointerUp}
    >
      <planeGeometry args={[gp.size ?? 100, gp.size ?? 100]} />
      <meshStandardMaterial color={gp.color ?? '#1a1a1a'} roughness={gp.roughness ?? 0.9} />
    </mesh>
  )
}

function DosimetryController() {
  useDosimetry()
  return null
}

function PhysicsController() {
  usePhysics()
  return null
}

export default function SceneRoot() {
  const config = useSceneStore(s => s.viewerConfig)
  if (!config) return null

  const cam = config.camera
  const ren = config.renderer
  const initialPosition = (cam.initial_position as [number, number, number]) ?? [0, 2, 5]

  const controlsRef = useRef<OrbitControlsImpl | null>(null)

  return (
    <Canvas
      camera={{
        fov: cam.fov,
        near: cam.near,
        far: cam.far,
        position: initialPosition,
      }}
      shadows={ren.shadows_enabled}
      gl={{
        antialias: ren.antialias ?? true,
        toneMapping: THREE.ACESFilmicToneMapping,
      }}
      style={{ position: 'absolute', inset: 0 }}
      tabIndex={0}
    >
      <color attach="background" args={[config.scene.background_color ?? '#0a0a0f']} />
      <SceneLighting />
      <Ground />
      <VoxelField />
      <SceneGeometry />
      <Environment />
      <BodyMesh />
      <Antenna />
      <DistanceLine />
      <RayPaths />
      <DosimetryController />
      <PhysicsController />
      <OrbitControls ref={controlsRef} makeDefault enableDamping />
      <CameraController controlsRef={controlsRef} initialPosition={initialPosition} />
    </Canvas>
  )
}
