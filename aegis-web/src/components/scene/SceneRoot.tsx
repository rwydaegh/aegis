import { useRef } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import type { ThreeEvent } from '@react-three/fiber'
import * as THREE from 'three'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useDosimetry } from '@/hooks/useDosimetry'
import BodyMesh from './BodyMesh'
import Antenna from './Antenna'

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

export default function SceneRoot() {
  const config = useSceneStore(s => s.viewerConfig)
  if (!config) return null

  const cam = config.camera
  const ren = config.renderer

  return (
    <Canvas
      camera={{
        fov: cam.fov,
        near: cam.near,
        far: cam.far,
        position: (cam.initial_position as [number, number, number]) ?? [0, 2, 5],
      }}
      shadows={ren.shadows_enabled}
      gl={{
        antialias: ren.antialias ?? true,
        toneMapping: THREE.ACESFilmicToneMapping,
      }}
      style={{ position: 'absolute', inset: 0 }}
    >
      <color attach="background" args={[config.scene.background_color ?? '#0a0a0f']} />
      <SceneLighting />
      <Ground />
      <BodyMesh />
      <Antenna />
      <DosimetryController />
      <OrbitControls makeDefault enableDamping />
    </Canvas>
  )
}
