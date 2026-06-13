import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useThree } from '@react-three/fiber'
import { Line, TransformControls } from '@react-three/drei'
import { toScene, toServer, type ServerPos } from '@/api/coordinates'
import { useStudioStore } from '../store'
import { colormapRgb } from './studioHelpers'

const LUT_SIZE = 256
// Reference window side: 4 cm^2 ICNIRP averaging area = 2 cm x 2 cm.
const REF_HALF = 0.01

const VERT_SHADER = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const FRAG_SHADER = /* glsl */ `
  precision highp float;
  uniform sampler2D dataTex;
  uniform sampler2D lut;
  uniform float vmin;
  uniform float vmax;
  uniform float logMode;
  uniform float opacity;
  varying vec2 vUv;
  void main() {
    float raw = texture2D(dataTex, vUv).r;
    float t;
    if (logMode > 0.5) {
      float eps = 1e-12;
      float lo = log(max(vmin, eps));
      float hi = log(max(vmax, max(vmin, eps) * 1.0001));
      float v = clamp(raw, max(vmin, eps), max(vmax, eps));
      t = (hi > lo) ? (log(v) - lo) / (hi - lo) : 0.0;
    } else {
      t = (vmax > vmin) ? (raw - vmin) / (vmax - vmin) : 0.0;
    }
    t = clamp(t, 0.0, 1.0);
    vec3 rgb = texture2D(lut, vec2(t, 0.5)).rgb;
    gl_FragColor = vec4(rgb, opacity);
  }
`

// Build a 1xN RGBA byte LUT texture from a named colormap.
function buildLutTexture(name: string): THREE.DataTexture {
  const data = new Uint8Array(LUT_SIZE * 4)
  for (let i = 0; i < LUT_SIZE; i++) {
    const t = i / (LUT_SIZE - 1)
    const [r, g, b] = colormapRgb(name, t)
    data[i * 4] = r
    data[i * 4 + 1] = g
    data[i * 4 + 2] = b
    data[i * 4 + 3] = 255
  }
  const tex = new THREE.DataTexture(data, LUT_SIZE, 1, THREE.RGBAFormat)
  tex.minFilter = THREE.LinearFilter
  tex.magFilter = THREE.LinearFilter
  tex.wrapS = THREE.ClampToEdgeWrapping
  tex.wrapT = THREE.ClampToEdgeWrapping
  tex.needsUpdate = true
  return tex
}

// The field slice rendered as a shader-coloured quad sitting at its true world
// position and extent. A TransformControls gizmo lets the user re-place / re-orient
// the plane; on drag end the settled centre + normal are written back to the store
// (in server Z-up coords), which the debounced slice hook turns into a refetch.
export default function StudioSlicePlane() {
  const sliceResult = useStudioStore((s) => s.sliceResult)
  const colormap = useStudioStore((s) => s.colormap)
  const scaleMode = useStudioStore((s) => s.scaleMode)
  const setPlane = useStudioStore((s) => s.setPlane)
  const setFocusXyz = useStudioStore((s) => s.setFocusXyz)

  const controls = useThree((s) => s.controls) as { enabled: boolean } | null

  // Stable object the TransformControls attaches to; children render inside it so
  // the plane, reference square, and focus dot move together.
  const planeObj = useRef(new THREE.Group())
  const draggingRef = useRef(false)

  // Data texture: rebuilt only when the slice scalar grid changes.
  const dataTex = useMemo(() => {
    if (!sliceResult) return null
    const [n1, n2] = sliceResult.shape
    const tex = new THREE.DataTexture(
      sliceResult.scalar,
      n2,
      n1,
      THREE.RedFormat,
      THREE.FloatType,
    )
    // 32F textures are not guaranteed to be linearly filterable on all GPUs, so
    // sample nearest (the grid is dense enough that this is imperceptible).
    tex.minFilter = THREE.NearestFilter
    tex.magFilter = THREE.NearestFilter
    tex.needsUpdate = true
    return tex
  }, [sliceResult])

  useEffect(() => () => dataTex?.dispose(), [dataTex])

  // LUT texture: rebuilt only when the colormap changes.
  const lutTex = useMemo(() => buildLutTexture(colormap), [colormap])
  useEffect(() => () => lutTex.dispose(), [lutTex])

  // Plane geometry: rebuilt only when the physical extent changes.
  const extent = sliceResult?.world.extent ?? 0.08
  const geometry = useMemo(() => new THREE.PlaneGeometry(extent, extent), [extent])
  useEffect(() => () => geometry.dispose(), [geometry])

  // Material is created once; uniforms are patched in effects below.
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: VERT_SHADER,
        fragmentShader: FRAG_SHADER,
        transparent: true,
        side: THREE.DoubleSide,
        uniforms: {
          dataTex: { value: null },
          lut: { value: null },
          vmin: { value: 0 },
          vmax: { value: 1 },
          logMode: { value: 0 },
          opacity: { value: 0.92 },
        },
      }),
    [],
  )
  useEffect(() => () => material.dispose(), [material])

  useEffect(() => {
    material.uniforms.dataTex.value = dataTex
    material.uniforms.lut.value = lutTex
    material.uniforms.vmin.value = sliceResult?.vmin ?? 0
    material.uniforms.vmax.value = sliceResult?.vmax ?? 1
    material.uniforms.logMode.value = scaleMode === 'log' ? 1 : 0
    material.needsUpdate = true
  }, [material, dataTex, lutTex, sliceResult, scaleMode])

  // Place + orient the plane from the (server-frame) world frame, converted to
  // scene Y-up. Skipped while dragging so the gizmo owns the transform.
  useEffect(() => {
    if (!sliceResult || draggingRef.current) return
    const { center, e1, e2 } = sliceResult.world
    const ex = new THREE.Vector3(...toScene(e1)).normalize()
    const ey = new THREE.Vector3(...toScene(e2)).normalize()
    const ez = new THREE.Vector3().crossVectors(ex, ey).normalize()
    const m = new THREE.Matrix4().makeBasis(ex, ey, ez)
    planeObj.current.quaternion.setFromRotationMatrix(m)
    planeObj.current.position.set(...toScene(center))
    planeObj.current.updateMatrixWorld()
  }, [sliceResult])

  // Reference square corners in the plane's local frame (z = small lift to avoid
  // z-fighting with the slice quad).
  const refSquare = useMemo<[number, number, number][]>(
    () => [
      [-REF_HALF, -REF_HALF, 0.0005],
      [REF_HALF, -REF_HALF, 0.0005],
      [REF_HALF, REF_HALF, 0.0005],
      [-REF_HALF, REF_HALF, 0.0005],
      [-REF_HALF, -REF_HALF, 0.0005],
    ],
    [],
  )

  const onDraggingChanged = (value: boolean) => {
    draggingRef.current = value
    if (controls) controls.enabled = !value
  }

  // On drag end, convert the settled transform back to server coords and commit.
  const onMouseUp = () => {
    onDraggingChanged(false)
    const obj = planeObj.current
    const centerScene: [number, number, number] = [obj.position.x, obj.position.y, obj.position.z]
    const normalScene = new THREE.Vector3(0, 0, 1).applyQuaternion(obj.quaternion).normalize()
    const centerServer = toServer(centerScene) as ServerPos
    const normalServer = toServer([normalScene.x, normalScene.y, normalScene.z]) as ServerPos
    setFocusXyz(centerServer)
    setPlane({ orientation: 'free', normalXyz: normalServer })
  }

  if (!sliceResult || !dataTex) return null

  return (
    <>
      <primitive object={planeObj.current}>
        <mesh geometry={geometry} material={material} />
        <Line points={refSquare} color="#ffffff" lineWidth={1.5} transparent opacity={0.8} />
        <mesh position={[0, 0, 0.001]}>
          <sphereGeometry args={[Math.max(extent * 0.02, 0.002), 16, 16]} />
          <meshBasicMaterial color="#00e5ff" depthTest={false} />
        </mesh>
      </primitive>

      <TransformControls
        object={planeObj.current}
        mode="translate"
        size={0.6}
        onMouseDown={() => onDraggingChanged(true)}
        onMouseUp={onMouseUp}
      />
    </>
  )
}
