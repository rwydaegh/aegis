import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { useThree } from '@react-three/fiber'
import { Line, TransformControls } from '@react-three/drei'
import { toScene, toServer, type ServerPos } from '@/api/coordinates'
import { useStudioStore } from '../store'
import { useStudioScales } from '../useStudioScales'
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
  uniform float dynamicRangeDb;
  uniform float opacity;
  varying vec2 vUv;
  void main() {
    // The grid ships row-major as scalar[i, j] with i indexing e1 (plane local x)
    // and j indexing e2 (local y). A DataTexture built (width=n2, height=n1) maps
    // its column to j (e2) and row to i (e1), so the texture is the transpose of
    // the plane's xy. Swap the sample coords so local x reads e1 and local y reads
    // e2, keeping the rendered field aligned with the true world axes.
    float raw = texture2D(dataTex, vec2(vUv.y, vUv.x)).r;
    float t;
    if (logMode > 0.5) {
      // Dynamic-range window of dynamicRangeDb dB below vmax, identical to the
      // body mesh (gainTFromLinear) and the volume, so "log" means one thing.
      float gMax = max(vmax, 1e-30);
      float gMin = gMax * pow(10.0, -dynamicRangeDb / 10.0);
      float lo = log2(gMin);
      float hi = log2(max(gMax, gMin * 1.0001));
      float v = clamp(raw, gMin, gMax);
      t = (hi > lo) ? (log2(v) - lo) / (hi - lo) : 0.0;
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
  const showSlice = useStudioStore((s) => s.showSlice)
  const setPlane = useStudioStore((s) => s.setPlane)
  const setFocusXyz = useStudioStore((s) => s.setFocusXyz)
  const screenshotMode = useStudioStore((s) => s.screenshotMode)
  const showRefSquare = useStudioStore((s) => s.showRefSquare)
  const showGizmo = useStudioStore((s) => s.showGizmo)

  // The resolved slice scale honours scope / mode / robust-clip / fixed range and,
  // for signed components (ReEx/y/z), the diverging coolwarm symmetric map.
  const { slice: display } = useStudioScales()

  const controls = useThree((s) => s.controls) as { enabled: boolean } | null

  // Stable object the TransformControls attaches to; children render inside it so
  // the plane, reference square, and focus dot move together.
  const planeObj = useMemo(() => new THREE.Group(), [])
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

  // LUT texture: rebuilt only when the (resolved) colormap changes.
  const lutTex = useMemo(() => buildLutTexture(display.colormap), [display.colormap])
  useEffect(() => () => lutTex.dispose(), [lutTex])

  // Plane geometry: rebuilt only when the physical extent changes. The backend
  // returns extent as [width along e1, height along e2] (metres), matching the
  // makeBasis(e1, e2, ...) orientation below.
  const [extentW, extentH] = sliceResult?.world.extent ?? [0.08, 0.08]
  const geometry = useMemo(() => new THREE.PlaneGeometry(extentW, extentH), [extentW, extentH])
  useEffect(() => () => geometry.dispose(), [geometry])

  // Material is created once; uniforms are patched in effects below.
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: VERT_SHADER,
        fragmentShader: FRAG_SHADER,
        transparent: true,
        // The slice is a single translucent quad. Writing depth would make it
        // occlude any transparent object that sorts after it (notably the 3D
        // field-volume cloud, whose box is centred on this plane), so the cloud
        // would vanish at the camera angles where the plane sorts first. Opaque
        // geometry (the body) still hides the slice via depthTest. So: no write.
        depthWrite: false,
        side: THREE.DoubleSide,
        uniforms: {
          dataTex: { value: null },
          lut: { value: null },
          vmin: { value: 0 },
          vmax: { value: 1 },
          logMode: { value: 0 },
          dynamicRangeDb: { value: 30 },
          opacity: { value: 0.92 },
        },
      }),
    [],
  )
  useEffect(() => () => material.dispose(), [material])

  useEffect(() => {
    material.uniforms.dataTex.value = dataTex
    material.uniforms.lut.value = lutTex
    material.uniforms.vmin.value = display.vmin
    material.uniforms.vmax.value = display.vmax
    material.uniforms.logMode.value = display.logMode ? 1 : 0
    material.uniforms.dynamicRangeDb.value = display.dynamicRangeDb
    material.needsUpdate = true
  }, [material, dataTex, lutTex, display])

  // Place + orient the plane from the (server-frame) world frame, converted to
  // scene Y-up. Skipped while dragging so the gizmo owns the transform.
  useEffect(() => {
    if (!sliceResult || draggingRef.current) return
    const { center, e1, e2 } = sliceResult.world
    const ex = new THREE.Vector3(...toScene(e1)).normalize()
    const ey = new THREE.Vector3(...toScene(e2)).normalize()
    const ez = new THREE.Vector3().crossVectors(ex, ey).normalize()
    const m = new THREE.Matrix4().makeBasis(ex, ey, ez)
    planeObj.quaternion.setFromRotationMatrix(m)
    planeObj.position.set(...toScene(center))
    planeObj.updateMatrixWorld()
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
    const obj = planeObj
    const centerScene: [number, number, number] = [obj.position.x, obj.position.y, obj.position.z]
    const normalScene = new THREE.Vector3(0, 0, 1).applyQuaternion(obj.quaternion).normalize()
    const centerServer = toServer(centerScene) as ServerPos
    const normalServer = toServer([normalScene.x, normalScene.y, normalScene.z]) as ServerPos
    setFocusXyz(centerServer)
    setPlane({ orientation: 'free', normalXyz: normalServer })
  }

  if (!showSlice || !sliceResult || !dataTex) return null

  return (
    <>
      <primitive object={planeObj}>
        <mesh geometry={geometry} material={material} />
        {showRefSquare && <Line points={refSquare} color="#ffffff" lineWidth={1.5} transparent opacity={0.8} />}
        {/* Focus marker: a flat black disc lying in the slice plane (the group's
            local z is the plane normal, so a circleGeometry is coplanar) rather
            than a sphere floating off the field. */}
        <mesh position={[0, 0, 0.001]}>
          <circleGeometry args={[Math.max(extentW * 0.02, 0.002), 48]} />
          <meshBasicMaterial color="#000000" side={THREE.DoubleSide} depthTest={false} />
        </mesh>
      </primitive>

      {/* The translate gizmo (RGB axis triad) is editing chrome: hidden for a
          clean figure capture, and behind a user toggle for an unobstructed view. */}
      {!screenshotMode && showGizmo && (
        <TransformControls
          object={planeObj}
          mode="translate"
          size={0.6}
          onMouseDown={() => onDraggingChanged(true)}
          onMouseUp={onMouseUp}
        />
      )}
    </>
  )
}
