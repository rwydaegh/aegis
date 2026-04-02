import { useRef, useMemo } from 'react'
import { Canvas, useThree, useFrame } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useDosimetry } from '@/hooks/useDosimetry'
import { useGpuStatus } from '@/hooks/useGpuStatus'
import { useMIMODosimetry } from '@/hooks/useMIMODosimetry'
import { useMIMOKeyboard } from '@/hooks/useMIMOKeyboard'
import { usePhysics } from '@/hooks/usePhysics'
import { useClickToPlace } from '@/hooks/useClickToPlace'
import BodyMesh from './BodyMesh'
import Antenna from './Antenna'
import DistanceLine from './DistanceLine'
import RayPaths from './RayPaths'
import VoxelField from './VoxelField'
import HullMesh from './HullMesh'
import SceneGeometry from './SceneGeometry'
import Environment from './Environment'
import FollowCamera from './FollowCamera'
import { EnvironmentOSM } from './EnvironmentOSM'
import { Environment3DTiles } from './Environment3DTiles'
import { useEnvironmentStore } from '@/stores/environment'
import { useMIMOStore } from '@/stores/mimo'
import BodyMeshInstance from './BodyMeshInstance'
import AntennaArrayViz from './AntennaArray'
import FocusPointMarker from './FocusPointMarker'
import SmartphoneModel from './SmartphoneModel'
import BaseStationMarkers from './BaseStationMarkers'
import { EnvironmentTerrain } from './EnvironmentTerrain'
import { CoverageOverlay } from './CoverageOverlay'
import { cameraState } from '@/lib/cameraState'

function GroundPlane() {
  const visible = useSceneStore(s => s.groundPlaneVisible)
  const config = useSceneStore(s => s.viewerConfig)
  const envSource = useEnvironmentStore(s => s.source)
  if (!visible || envSource !== 'none') return null
  const gp = config?.scene?.ground_plane as Record<string, unknown> | undefined
  const size = (gp?.size as number) ?? 500
  const color = (gp?.color as string) ?? '#1a1a20'
  const opacity = (gp?.opacity as number) ?? 0.5
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
      <planeGeometry args={[size, size]} />
      <meshStandardMaterial color={color} transparent opacity={opacity} roughness={1} />
    </mesh>
  )
}

function SceneGrid() {
  const visible = useSceneStore(s => s.gridVisible)
  const config = useSceneStore(s => s.viewerConfig)
  const envSource = useEnvironmentStore(s => s.source)
  if (!visible || envSource !== 'none') return null
  const grid = config?.scene?.grid as Record<string, unknown> | undefined
  const size = (grid?.size as number) ?? 200
  const divisions = (grid?.divisions as number) ?? 100
  const yOffset = (grid?.y_offset as number) ?? -0.01
  const color = (grid?.color as string) ?? '#666666'
  const lineColor = (grid?.line_color as string) ?? '#444444'
  return (
    <gridHelper args={[size, divisions, color, lineColor]} position={[0, yOffset, 0]} />
  )
}

/**
 * Syncs Three.js camera position/target to the module-level cameraState
 * every frame, so share links can read it without triggering React re-renders.
 */
function CameraSyncer({ controlsRef }: { controlsRef: React.RefObject<OrbitControlsImpl | null> }) {
  const { camera } = useThree()
  useFrame(() => {
    cameraState.position = camera.position.toArray() as [number, number, number]
    const controls = controlsRef.current
    if (controls) {
      const t = controls.target as THREE.Vector3
      cameraState.target = t.toArray() as [number, number, number]
    }
  })
  return null
}

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
 * Also applies a camera override from share links if one is pending.
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

    // Check for a share link camera override first (takes priority)
    const override = useUIStore.getState().cameraOverride
    if (override) {
      camera.position.set(...override.position)
      const target = controls.target as THREE.Vector3
      target.set(...override.target)
      controls.update()
      useUIStore.getState().setCameraOverride(null)
      return
    }

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
  useGpuStatus()
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
  const cameraMode = useUIStore(s => s.cameraMode)
  const caps = useSceneStore(s => s.capabilities)
  const deviceOffsets = caps?.body_device_offsets ?? {}
  const fallbackOffset: [number, number, number] = [0, 0.30, 1.4]

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
          <SmartphoneModel
            position={user.position}
            rotationY={user.orientation}
            deviceOffset={deviceOffsets[user.phantomName] as [number, number, number] ?? fallbackOffset}
          />
        </group>
      ))}
      {arrayConfig && <AntennaArrayViz config={arrayConfig} freqHz={freqGhz * 1e9} showPattern={showArrayPattern && cameraMode === 'orbit'} weights={precoderWeights} />}
      {arrayConfig && <FocusPointMarker />}
    </>
  )
}

function hasWebGL(): boolean {
  try {
    const canvas = document.createElement('canvas')
    return !!(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

function WebGLUnavailable() {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-background">
      <div className="text-center max-w-md px-6">
        <p className="text-destructive font-medium mb-2">WebGL is not available</p>
        <p className="text-muted-foreground text-sm">
          Your browser or device does not support WebGL, which is required for the 3D viewer.
          Try using a different browser, enabling hardware acceleration, or updating your graphics drivers.
        </p>
      </div>
    </div>
  )
}

export default function SceneRoot() {
  const webglAvailable = useMemo(() => hasWebGL(), [])
  const config = useSceneStore(s => s.viewerConfig)
  const bodyMeshVisible = useSceneStore(s => s.bodyMeshVisible)
  const bodyOffset = useSimulationStore(s => s.bodyOffset)
  const cameraMode = useUIStore(s => s.cameraMode)
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const envSource = useEnvironmentStore(s => s.source)
  const controlsRef = useRef<OrbitControlsImpl | null>(null)
  if (!webglAvailable) return <WebGLUnavailable />
  if (!config) return null

  const cam = config.camera
  const ren = config.renderer
  const initialPosition = (cam.initial_position as [number, number, number]) ?? [0, 2, 5]

  const sceneContent = (
    <>
      <color attach="background" args={[config.scene.background_color ?? '#0a0a0f']} />
      <SceneLighting />
      <ClickPlane />
      {(envSource === 'none' || envSource === 'voxels') && (
        <>
          <VoxelField />
          <HullMesh />
          <SceneGeometry />
          <Environment />
        </>
      )}
      {envSource === 'osm' && <EnvironmentOSM />}
      {bodyMeshVisible && (mimoEnabled ? (
        <MIMOScene />
      ) : (
        <>
          <BodyMesh />
          <Antenna />
          <DistanceLine />
        </>
      ))}
      <RayPaths />
      <GroundPlane />
      <SceneGrid />
      <EnvironmentTerrain />
      <BaseStationMarkers />
      <CoverageOverlay />
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
          <CameraSyncer controlsRef={controlsRef} />
        </>
      )}
    </>
  )

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
        logarithmicDepthBuffer: true,
      }}
      style={{ position: 'absolute', inset: 0 }}
      tabIndex={0}
    >
      {envSource === '3dtiles' ? (
        <Environment3DTiles>{sceneContent}</Environment3DTiles>
      ) : (
        sceneContent
      )}
    </Canvas>
  )
}
