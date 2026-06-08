import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import * as THREE from 'three'
import { useLabStore } from '../store'

// Incident ray length and where it terminates (pelvis origin in the raw frame).
const RAY_LENGTH = 1.2
const BODY_CENTER = new THREE.Vector3(0, 0, 0)

type Vec3 = [number, number, number]

// Far-field plane-wave incidence visual. The propagation direction matches the
// server `_far_field`: k_hat = [sin(theta)cos(phi), sin(theta)sin(phi), cos(theta)].
// We draw an arrow from `bodyCenter - L*k_hat` into `bodyCenter` (pointing along
// +k_hat), two-toned for the TE/TM transverse basis, plus a polarisation ellipse
// at the tail whose axes are driven by polAngle.
export default function FarFieldRay() {
  const thetaInc = useLabStore((s) => s.thetaInc)
  const phiInc = useLabStore((s) => s.phiInc)
  const polAngle = useLabStore((s) => s.polAngle)

  const { tail, head, headDir, eTheta, ePhi, ellipse, polLine } = useMemo(() => {
    const st = Math.sin(thetaInc)
    const ct = Math.cos(thetaInc)
    const cp = Math.cos(phiInc)
    const sp = Math.sin(phiInc)

    const k = new THREE.Vector3(st * cp, st * sp, ct).normalize()
    const tailV = BODY_CENTER.clone().addScaledVector(k, -RAY_LENGTH)
    const headV = BODY_CENTER.clone()

    // Spherical transverse basis. e_theta is the TM (in-plane) direction, e_phi
    // is the TE (horizontal) direction; both are orthogonal to k.
    const eThetaV = new THREE.Vector3(ct * cp, ct * sp, -st).normalize()
    const ePhiV = new THREE.Vector3(-sp, cp, 0).normalize()

    // Polarisation ellipse in the transverse plane at the tail. Semi-axes grow
    // with cos/sin(polAngle) so the shape morphs from TM-aligned to TE-aligned.
    const RING = 0.18
    const axTheta = RING * (0.25 + Math.abs(Math.cos(polAngle)))
    const axPhi = RING * (0.25 + Math.abs(Math.sin(polAngle)))
    const ringPts: Vec3[] = []
    const N = 48
    for (let i = 0; i <= N; i++) {
      const u = (i / N) * Math.PI * 2
      const p = tailV
        .clone()
        .addScaledVector(eThetaV, axTheta * Math.cos(u))
        .addScaledVector(ePhiV, axPhi * Math.sin(u))
      ringPts.push([p.x, p.y, p.z])
    }

    // Linear polarisation direction (double-headed) at the tail.
    const pHat = eThetaV
      .clone()
      .multiplyScalar(Math.cos(polAngle))
      .addScaledVector(ePhiV, Math.sin(polAngle))
      .normalize()
    const PL = 0.22
    const polA = tailV.clone().addScaledVector(pHat, PL)
    const polB = tailV.clone().addScaledVector(pHat, -PL)

    // Short TE/TM basis markers at the tail.
    const TM = 0.12
    const eThetaPts: Vec3[] = [
      [tailV.x, tailV.y, tailV.z],
      [tailV.x + eThetaV.x * TM, tailV.y + eThetaV.y * TM, tailV.z + eThetaV.z * TM],
    ]
    const ePhiPts: Vec3[] = [
      [tailV.x, tailV.y, tailV.z],
      [tailV.x + ePhiV.x * TM, tailV.y + ePhiV.y * TM, tailV.z + ePhiV.z * TM],
    ]

    return {
      tail: [tailV.x, tailV.y, tailV.z] as Vec3,
      head: [headV.x, headV.y, headV.z] as Vec3,
      headDir: k,
      eTheta: eThetaPts,
      ePhi: ePhiPts,
      ellipse: ringPts,
      polLine: [
        [polA.x, polA.y, polA.z],
        [polB.x, polB.y, polB.z],
      ] as Vec3[],
    }
  }, [thetaInc, phiInc, polAngle])

  // Cone head: orient +Y (cone default axis) onto k.
  const headQuat = useMemo(() => {
    const q = new THREE.Quaternion()
    q.setFromUnitVectors(new THREE.Vector3(0, 1, 0), headDir)
    return q
  }, [headDir])

  const conePos = useMemo<Vec3>(() => {
    const p = new THREE.Vector3(...head).addScaledVector(headDir, -0.04)
    return [p.x, p.y, p.z]
  }, [head, headDir])

  return (
    <group>
      {/* Shaft (propagation direction into the body) */}
      <Line points={[tail, head]} color="#ffb703" lineWidth={3} />

      {/* Arrow head */}
      <mesh position={conePos} quaternion={headQuat}>
        <coneGeometry args={[0.03, 0.08, 16]} />
        <meshStandardMaterial color="#ffb703" emissive="#7a5300" emissiveIntensity={0.5} />
      </mesh>

      {/* TM (e_theta) and TE (e_phi) basis markers */}
      <Line points={eTheta} color="#e63946" lineWidth={2} />
      <Line points={ePhi} color="#2a9d8f" lineWidth={2} />

      {/* Polarisation ellipse + linear polarisation direction */}
      <Line points={ellipse} color="#a78bfa" lineWidth={2} transparent opacity={0.85} />
      <Line points={polLine} color="#ffffff" lineWidth={2} />
    </group>
  )
}
