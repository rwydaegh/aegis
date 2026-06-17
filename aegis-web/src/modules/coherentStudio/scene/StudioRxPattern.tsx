import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { jetColor } from '@/lib/colormap'
import { toServer } from '@/api/coordinates'
import { useStudioStore } from '../store'
import { rxGain } from '../panels/studioRxPattern'

// The receive (UE) antenna pattern, drawn as a lobe balloon at the steering
// focus (which IS r_UE: the studio computes the channel h at the focus). Vertex
// radius is proportional to |C_R(k)| in that direction, so a dipole reads as a
// donut, a patch as a forward lobe, and isotropic / vertical as a featureless
// sphere.
//
// The backend builds C_R via make_rx_response(kind, freq) with its defaults
// (axis = +z, no rotation), so the antenna is Z-up in the world frame. We
// evaluate the pattern in that server frame and let the balloon inherit the
// orientation, rather than idealising it to face the base station.

interface StudioRxPatternProps {
  /** Focus position in scene (Y-up) coordinates; the balloon is centred here. */
  focusScene: [number, number, number]
}

// Compress the radial dynamic range so deep nulls do not collapse the mesh to a
// point (matches the base-station pattern balloon's lobeGamma).
const LOBE_GAMMA = 0.42

// Minimum drawn radius as a fraction of the peak, so deep nulls (e.g. a dipole's
// end-fire zero) keep a small visible shell instead of touching the focus point
// at the centre. The true (un-floored) gain still drives the colour, so a null
// reads as a blue dimple at this floor rather than collapsing onto the hotspot.
const MIN_NORM = 0.12

// Build a UNIT-radius lobe (max radius 1) for the given antenna kind; the caller
// scales it to the user's extent. Colour is the displayed radius (gn^gamma)
// mapped through jet, so the full colormap spreads across the lobe instead of
// pinning the whole high-gain region to red as a dB mapping would.
function buildRxGeometry(kind: string): THREE.BufferGeometry {
  const base = new THREE.IcosahedronGeometry(1, 5)
  const posAttr = base.attributes.position as THREE.BufferAttribute
  const nV = posAttr.count

  const gains = new Float32Array(nV)
  const dirs: THREE.Vector3[] = []
  let gMax = 0

  for (let i = 0; i < nV; i++) {
    const d = new THREE.Vector3(posAttr.getX(i), posAttr.getY(i), posAttr.getZ(i)).normalize()
    dirs.push(d)
    // Sample C_R in the server (Z-up) frame the backend uses, so the lobe is
    // oriented exactly as the precoder sees the antenna.
    const [sx, sy, sz] = toServer([d.x, d.y, d.z])
    const g = rxGain(kind, sx, sy, sz)
    gains[i] = g
    if (g > gMax) gMax = g
  }
  if (gMax < 1e-12) gMax = 1

  const colors = new Float32Array(nV * 3)
  for (let i = 0; i < nV; i++) {
    const gn = gains[i] / gMax
    // True normalised gain in [0, 1] (drives the colour) and the drawn radius,
    // affinely lifted off zero so the peak still reaches 1 but nulls sit at
    // MIN_NORM instead of the centre.
    const norm = Math.max(gn, 1e-9) ** LOBE_GAMMA
    const drawNorm = MIN_NORM + (1 - MIN_NORM) * norm
    const d = dirs[i]
    posAttr.setXYZ(i, d.x * drawNorm, d.y * drawNorm, d.z * drawNorm)

    const [cr, cg, cb] = jetColor(norm)
    colors[i * 3] = cr
    colors[i * 3 + 1] = cg
    colors[i * 3 + 2] = cb
  }

  posAttr.needsUpdate = true
  base.setAttribute('color', new THREE.BufferAttribute(colors, 3))
  base.computeVertexNormals()
  return base
}

export default function StudioRxPattern({ focusScene }: StudioRxPatternProps) {
  const ueAntenna = useStudioStore((s) => s.ueAntenna)
  const extentM = useStudioStore((s) => s.rxPatternExtentM)

  const geo = useMemo(() => buildRxGeometry(ueAntenna), [ueAntenna])
  useEffect(() => () => geo.dispose(), [geo])

  // The receive origin (r_UE) is marked by the slice's black focus disc, so the
  // lobe needs no separate origin sphere.
  return (
    <group position={focusScene}>
      {/* Unit lobe scaled to the user's max extent (metres). */}
      <mesh geometry={geo} scale={extentM}>
        <meshStandardMaterial
          vertexColors
          transparent
          opacity={0.55}
          depthWrite={false}
          side={THREE.DoubleSide}
          metalness={0.1}
          roughness={0.7}
        />
      </mesh>
    </group>
  )
}
