import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { jetColor, gainTFromLinear } from '@/lib/colormap'
import { toServer } from '@/api/coordinates'
import { useStudioStore } from '../store'
import { rxGain } from '../panels/studioRxPattern'

// The receive (UE) antenna pattern, drawn as a lobe balloon at the steering
// focus (which IS r_UE: the studio computes the channel h at the focus). Vertex
// radius is proportional to |C_R(k)| in that direction and the surface is
// jet-coloured by magnitude in dB, so a dipole reads as a donut, a patch as a
// forward lobe, and isotropic / vertical as a featureless sphere.
//
// The backend builds C_R via make_rx_response(kind, freq) with its defaults
// (axis = +z, no rotation), so the antenna is Z-up in the world frame. We
// evaluate the pattern in that server frame and let the balloon inherit the
// orientation, rather than idealising it to face the base station.

interface StudioRxPatternProps {
  /** Focus position in scene (Y-up) coordinates; the balloon is centred here. */
  focusScene: [number, number, number]
}

// Physical-ish size of the lobe in metres. The phantom is ~1.7 m tall, so a
// half-metre balloon at the focus is visible without engulfing the body.
const BASE_RADIUS = 0.5
// Compress the radial dynamic range so deep nulls do not collapse the mesh to a
// point (matches the base-station pattern balloon's lobeGamma).
const LOBE_GAMMA = 0.42
// Colour dynamic range in dB below the peak.
const DYN_DB = 30

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
    const rr = BASE_RADIUS * Math.max(gn, 1e-9) ** LOBE_GAMMA
    const d = dirs[i]
    posAttr.setXYZ(i, d.x * rr, d.y * rr, d.z * rr)

    const t = gainTFromLinear(gains[i], gMax, DYN_DB)
    const [cr, cg, cb] = jetColor(t)
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

  const geo = useMemo(() => buildRxGeometry(ueAntenna), [ueAntenna])
  useEffect(() => () => geo.dispose(), [geo])

  return (
    <group position={focusScene}>
      <mesh geometry={geo}>
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
      {/* Marker at the receive origin (r_UE). */}
      <mesh>
        <sphereGeometry args={[0.025, 16, 16]} />
        <meshStandardMaterial color="#ffffff" emissive="#888888" emissiveIntensity={0.5} />
      </mesh>
    </group>
  )
}
