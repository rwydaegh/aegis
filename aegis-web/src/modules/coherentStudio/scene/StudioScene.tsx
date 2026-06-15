import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useThree, type ThreeEvent } from '@react-three/fiber'
import { OrbitControls, Line, Html } from '@react-three/drei'
import AntennaArray from '@/components/scene/AntennaArray'
import FocusPointMarker from '@/components/scene/FocusPointMarker'
import BodyMeshInstance from '@/components/scene/BodyMeshInstance'
import { toScene, toServer, type ServerPos } from '@/api/coordinates'
import type { Vec3 } from '../api'
import type { ArrayConfig } from '@/api/types'
import { useStudioStore } from '../store'
import { useStudioRays } from '../useStudioRays'
import { useStudioScales } from '../useStudioScales'
import { colormapRgb, snapFocusToSkin } from './studioHelpers'
import StudioSlicePlane from './StudioSlicePlane'
import StudioVolume from './StudioVolume'
import StudioRays from './StudioRays'

// Base station position (server Z-up metres), fixed by the e11 geometry.
const BS_SERVER: ServerPos = [-13, 0, 3]

interface StudioSceneProps {
  /** Bumped by the module's "snap to BS axis" button to reframe the camera. */
  snapSignal: number
}

// Build a renderable phantom geometry: a non-indexed triangle soup with a colour
// attribute that BodyMeshInstance overwrites per face.
function usePhantomGeometry(): THREE.BufferGeometry | null {
  const phantom = useStudioStore((s) => s.phantom)
  const geometry = useMemo(() => {
    if (!phantom) return null
    const g = new THREE.BufferGeometry()
    // Clone the vertex buffer: g.rotateX mutates the position array IN PLACE, and
    // phantom.vertices is the shared store buffer. If we wrapped it directly, a
    // re-run of this memo on the same buffer (StrictMode double-invoke, or a
    // re-fetch on phantom switch) would rotate the already-rotated data again and
    // tip the body onto the floor. Rotating a private copy keeps it idempotent.
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(phantom.vertices), 3))
    g.setAttribute('color', new THREE.BufferAttribute(new Float32Array(phantom.vertices.length), 3))
    // Phantom vertices ship in the e11 world frame (Z-up). The scene is Y-up, so
    // rotate -90 deg about X (the exact rotation toScene applies to points) to
    // land the body where the toScene-converted focus, slice, and camera expect.
    g.rotateX(-Math.PI / 2)
    g.computeVertexNormals()
    return g
  }, [phantom])

  useEffect(() => () => geometry?.dispose(), [geometry])
  return geometry
}

// Reframe the camera to look down the BS -> focus beam axis when snapSignal bumps.
function CameraRig({ snapSignal, focusScene }: { snapSignal: number; focusScene: [number, number, number] }) {
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as
    | { target: THREE.Vector3; update: () => void }
    | null

  useEffect(() => {
    if (snapSignal === 0) return
    const bs = new THREE.Vector3(...toScene(BS_SERVER))
    const focus = new THREE.Vector3(...focusScene)
    const dir = focus.clone().sub(bs).normalize()
    // Sit slightly behind and above the BS, looking along the beam.
    const camPos = bs.clone().addScaledVector(dir, -2).add(new THREE.Vector3(0, 1, 0))
    camera.position.copy(camPos)
    if (controls) {
      controls.target.copy(focus)
      controls.update()
    } else {
      camera.lookAt(focus)
    }
  }, [snapSignal, focusScene, camera, controls])

  return null
}

export default function StudioScene({ snapSignal }: StudioSceneProps) {
  const focusXyz = useStudioStore((s) => s.focusXyz)
  const setFocusXyz = useStudioStore((s) => s.setFocusXyz)
  const focusMode = useStudioStore((s) => s.focusMode)
  const phantom = useStudioStore((s) => s.phantom)
  const frequencyGhz = useStudioStore((s) => s.frequencyGhz)
  const bodyMap = useStudioStore((s) => s.bodyMap)
  const showRays = useStudioStore((s) => s.showRays)
  const showArrayPattern = useStudioStore((s) => s.showArrayPattern)
  const wireframe = useStudioStore((s) => s.wireframe)
  const pickFocusOnBody = useStudioStore((s) => s.pickFocusOnBody)

  const rays = useStudioRays()
  const geometry = usePhantomGeometry()
  const { body: bodyScale } = useStudioScales()

  // Steering focus: in at-skin mode the slice endpoint snaps the focus onto the
  // nearest body surface, so mirror that here (same nearest-centroid search) for
  // the focus marker and beam axis to line up with the field that is computed.
  const steeringFocus = useMemo<[number, number, number]>(
    () => (focusMode === 'at-skin' ? snapFocusToSkin(focusXyz, phantom?.centroids) : focusXyz),
    [focusMode, focusXyz, phantom],
  )

  const focusScene = useMemo<[number, number, number]>(() => toScene(steeringFocus), [steeringFocus])
  const bsScene = useMemo<[number, number, number]>(() => toScene(BS_SERVER), [])

  // Beam axis: BS -> focus. Range and downtilt computed in server coords (rigid
  // transform preserves lengths and angles).
  const { rangeM, downDeg } = useMemo(() => {
    const dx = BS_SERVER[0] - steeringFocus[0]
    const dy = BS_SERVER[1] - steeringFocus[1]
    const dz = BS_SERVER[2] - steeringFocus[2]
    const horiz = Math.hypot(dx, dy)
    return {
      rangeM: Math.hypot(dx, dy, dz),
      downDeg: (Math.atan2(dz, horiz) * 180) / Math.PI,
    }
  }, [steeringFocus])

  const beamMidScene = useMemo<[number, number, number]>(
    () => [
      (bsScene[0] + focusScene[0]) / 2,
      (bsScene[1] + focusScene[1]) / 2,
      (bsScene[2] + focusScene[2]) / 2,
    ],
    [bsScene, focusScene],
  )

  // 16x16 URA broadside pointed from the BS toward the focus (scene coords).
  const arrayConfig = useMemo<ArrayConfig>(() => {
    const dir = new THREE.Vector3(
      focusScene[0] - bsScene[0],
      focusScene[1] - bsScene[1],
      focusScene[2] - bsScene[2],
    ).normalize()
    return {
      type: 'upa',
      n_h: 16,
      n_v: 16,
      d_h_wavelengths: 0.5,
      d_v_wavelengths: 0.5,
      position: bsScene,
      broadside: [dir.x, dir.y, dir.z],
      element_pattern: 'patch',
    }
  }, [bsScene, focusScene])

  // Studio drives its own colour scale (viridis, own log toggle) so it never
  // perturbs the main viewer's shared useUIStore state.
  const colorFn = useMemo(() => {
    return (t: number): [number, number, number] => {
      const [r, g, b] = colormapRgb(bodyScale.colormap, t)
      return [r / 255, g / 255, b / 255]
    }
  }, [bodyScale.colormap])

  const sabArray = useMemo(
    () => (bodyMap ? Float32Array.from(bodyMap.values) : null),
    [bodyMap],
  )

  // Pick the beam focus by clicking the body: convert the world-space hit point
  // (scene Y-up) back to the server Z-up frame the focus store expects.
  const onBodyClick = (e: ThreeEvent<MouseEvent>) => {
    if (!pickFocusOnBody) return
    e.stopPropagation()
    const p = e.point
    setFocusXyz(toServer([p.x, p.y, p.z]) as Vec3)
  }

  return (
    <>
      <color attach="background" args={['#0a0a0f']} />

      <ambientLight intensity={0.55} />
      <directionalLight position={[5, 10, 5]} intensity={0.9} />
      <hemisphereLight args={['#b1e1ff', '#2c2c2c', 0.35]} />

      <gridHelper args={[30, 30, '#444444', '#222222']} position={[0, 0, 0]} />

      <AntennaArray config={arrayConfig} freqHz={frequencyGhz * 1e9} showPattern={showArrayPattern} />

      {/* Beam axis + range / downtilt label. */}
      <Line points={[bsScene, focusScene]} color="#00e5ff" lineWidth={1} dashed dashSize={0.3} gapSize={0.2} transparent opacity={0.5} />
      <Html position={beamMidScene} center style={{ pointerEvents: 'none' }}>
        <div
          style={{
            color: '#9fe',
            fontSize: 11,
            background: 'rgba(10,10,15,0.7)',
            padding: '2px 6px',
            borderRadius: 4,
            whiteSpace: 'nowrap',
          }}
        >
          {rangeM.toFixed(1)} m, {Math.round(downDeg)} deg down
        </div>
      </Html>

      {showRays && <StudioRays rays={rays} />}
      <FocusPointMarker focusPoint={focusScene} arrayPosition={bsScene} />
      <StudioSlicePlane />
      <StudioVolume />

      <BodyMeshInstance
        geometry={geometry}
        sabArray={sabArray}
        position={[0, 0, 0]}
        rotationY={0}
        displayQuantityOverride="sab"
        legendScaleOverride={bodyScale.logMode ? 'dB' : 'linear'}
        dynamicRangeDbOverride={bodyScale.dynamicRangeDb}
        colormapLockedOverride
        colormapLockedMaxOverride={bodyScale.vmax}
        ratioModeOverride={false}
        wireframeOverride={wireframe}
        colorFn={colorFn}
        doubleSided
        onClick={pickFocusOnBody ? onBodyClick : undefined}
      />

      <CameraRig snapSignal={snapSignal} focusScene={focusScene} />
      <OrbitControls makeDefault enableDamping target={focusScene} />
    </>
  )
}
