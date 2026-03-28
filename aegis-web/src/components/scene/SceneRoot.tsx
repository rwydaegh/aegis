import { useRef } from 'react'
import { Canvas, useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useDosimetry } from '@/hooks/useDosimetry'
import { useMIMODosimetry } from '@/hooks/useMIMODosimetry'
import { useMIMOKeyboard } from '@/hooks/useMIMOKeyboard'
import { usePhysics } from '@/hooks/usePhysics'
import { useClickToPlace } from '@/hooks/useClickToPlace'
import BodyMesh from './BodyMesh'
import Antenna from './Antenna'
import DistanceLine from './DistanceLine'
import RayPaths from './RayPaths'
import VoxelField from './VoxelField'
import SceneGeometry from './SceneGeometry'
import Environment from './Environment'
import FollowCamera from './FollowCamera'
import { useMIMOStore } from '@/stores/mimo'
import BodyMeshInstance from './BodyMeshInstance'
import AntennaArrayViz from './AntennaArray'
import FocusPointMarker from './FocusPointMarker'
import SmartphoneModel from './SmartphoneModel'
import BaseStationMarkers from './BaseStationMarkers'

// Body is roughly 1.2 m tall, centered at origin, feet at y=0
const BODY_TARGET = new THREE.Vector3(0, 0.6, 0)

// Camera preset offsets relative to body center (body center ~ 0.6m above feet)
const PRESET_OFFSETS: Record<string, { posOffset: [number, number, number]; targetOffset: [number, number, number] }> = {
  front: { posOffset: [0, 0.4, 4], targetOffset: [0, 0.6, 0] },
  side:  { posOffset: [4, 0.4, 0], targetOffset: [0, 0.6, 0] },
  top:   { posOffset: [0, 6, 0.01], targetOffset: [0, 0, 0] },
  focus: { posOffset: [0, 0, 2.5], targetOffset: [0, 0.6, 0] },
}

/**
 * Listens to ui.cameraPreset and smoothly transitions the camera + orbit target.
 * Presets are relative to the current body position.
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

    // Get current body position to offset presets (MIMO-aware)
    const mimoState = useMIMOStore.getState()
    let bodyPos: [number, number, number]
    if (mimoState.enabled && mimoState.controlledUserId) {
      const user = mimoState.users.get(mimoState.controlledUserId)
      bodyPos = user?.position ?? useSimulationStore.getState().bodyOffset
    } else {
      bodyPos = useSimulationStore.getState().bodyOffset
    }
    const [bx, by, bz] = bodyPos

    let dest: { position: [number, number, number]; target: [number, number, number] }
    if (preset === 'reset') {
      dest = {
        position: [bx + initialPosition[0], by + initialPosition[1], bz + initialPosition[2]],
        target: [bx, by + 0.6, bz],
      }
    } else {
      const p = PRESET_OFFSETS[preset] ?? PRESET_OFFSETS.front
      dest = {
        position: [bx + p.posOffset[0], by + p.posOffset[1], bz + p.posOffset[2]],
        target: [bx + p.targetOffset[0], by + p.targetOffset[1], bz + p.targetOffset[2]],
      }
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
  const light = config.lighting

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

/** Invisible click plane for antenna placement in empty space (y=0). */
function ClickPlane() {
  const clickHandlers = useClickToPlace()
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} {...clickHandlers}>
      <planeGeometry args={[500, 500]} />
      <meshBasicMaterial transparent opacity={0} side={THREE.DoubleSide} depthWrite={false} />
    </mesh>
  )
}

/**
 * On mount, move the camera + orbit target to look at the body's actual position.
 * This handles the case where body_placement puts the body far from the origin.
 */
function CameraInitializer({ controlsRef, initialOffset }: {
  controlsRef: React.RefObject<OrbitControlsImpl | null>
  initialOffset: [number, number, number]
}) {
  const { camera } = useThree()
  const initialized = useRef(false)

  useFrame(() => {
    if (initialized.current) return
    const controls = controlsRef.current
    if (!controls) return
    initialized.current = true

    const [bx, by, bz] = initialOffset
    // Only relocate if body is significantly off-origin
    if (Math.abs(bx) > 1 || Math.abs(bz) > 1) {
      const target = controls.target as THREE.Vector3
      target.set(bx, by + 0.6, bz)
      camera.position.set(bx, by + 2, bz + 5)
      controls.update()
    }
  })

  return null
}

function DosimetryController() {
  useDosimetry()
  return null
}

function MIMODosimetryController() {
  useMIMODosimetry()
  return null
}

function MIMOKeyboardController() {
  useMIMOKeyboard()
  return null
}

function PhysicsController() {
  usePhysics()
  return null
}

function MIMOScene() {
  const users = useMIMOStore(s => s.users)
  const focusedUserId = useMIMOStore(s => s.focusedUserId)
  const showAllHeatmaps = useMIMOStore(s => s.showAllHeatmaps)
  const showArrayPattern = useMIMOStore(s => s.showArrayPattern)
  const precoderWeights = useMIMOStore(s => s.precoderWeights)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)
  const setFocusedUser = useMIMOStore(s => s.setFocusedUser)
  const freqGhz = useSimulationStore(s => s.freqGhz)

  return (
    <>
      {[...users.values()].map(user => (
        <group key={user.userId}>
          <BodyMeshInstance
            geometry={user.bodyGeometry}
            sabArray={showAllHeatmaps ? user.sabArray : (
              user.userId === focusedUserId ? user.sabArray : null
            )}
            stats={user.stats}
            position={user.position}
            rotationY={user.orientation}
            opacity={user.userId === focusedUserId ? 1.0 : 0.7}
            onClick={() => setFocusedUser(user.userId)}
          />
          <SmartphoneModel position={user.position} rotationY={user.orientation} />
        </group>
      ))}
      {arrayConfig && <AntennaArrayViz config={arrayConfig} freqHz={freqGhz * 1e9} showPattern={showArrayPattern} weights={precoderWeights} />}
      {arrayConfig && <FocusPointMarker />}
    </>
  )
}

export default function SceneRoot() {
  const config = useSceneStore(s => s.viewerConfig)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const cameraMode = useUIStore(s => s.cameraMode)
  const mimoEnabled = useMIMOStore(s => s.enabled)
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
      shadows={ren.shadows_enabled ? { type: THREE.PCFShadowMap } : false}
      gl={{
        antialias: ren.antialias ?? true,
        toneMapping: THREE.ACESFilmicToneMapping,
        preserveDrawingBuffer: true,
      }}
      style={{ position: 'absolute', inset: 0 }}
      tabIndex={0}
    >
      <color attach="background" args={[config.scene.background_color ?? '#0a0a0f']} />
      <SceneLighting />
      <ClickPlane />
      <VoxelField />
      <SceneGeometry />
      <Environment />
      {mimoEnabled ? (
        <MIMOScene />
      ) : (
        <>
          <BodyMesh />
          <Antenna />
          <DistanceLine />
        </>
      )}
      <RayPaths />
      <BaseStationMarkers />
      <DosimetryController />
      <MIMODosimetryController />
      <MIMOKeyboardController />
      <PhysicsController />
      <FollowCamera />
      {cameraMode === 'orbit' && (
        <>
          <OrbitControls ref={controlsRef} makeDefault enableDamping />
          <CameraController controlsRef={controlsRef} initialPosition={initialPosition} />
          <CameraInitializer controlsRef={controlsRef} initialOffset={bodyOffset} />
        </>
      )}
    </Canvas>
  )
}
