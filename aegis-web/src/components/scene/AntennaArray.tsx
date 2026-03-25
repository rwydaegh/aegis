import { useMemo, useRef, useEffect } from 'react'
import * as THREE from 'three'
import type { ArrayConfig } from '@/api/types'

interface AntennaArrayProps {
  config: ArrayConfig
  freqHz: number
}

const ELEMENT_COLOR = new THREE.Color(0.8, 0.2, 0.2)
const POLE_RADIUS = 0.04
const POLE_COLOR = new THREE.Color(0.4, 0.4, 0.4)
const ARROW_COLOR = new THREE.Color(1, 0.4, 0)
const MIN_ELEMENT_RADIUS = 0.005
const MAX_ELEMENT_RADIUS = 0.03

export default function AntennaArray({ config, freqHz }: AntennaArrayProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null)
  const nElements = config.n_h * config.n_v

  // Compute element positions in local coords (array-centered)
  const localPositions = useMemo(() => {
    const positions: THREE.Vector3[] = []
    const broadside = new THREE.Vector3(...config.broadside).normalize()

    // Build local coordinate frame
    const up = new THREE.Vector3(0, 1, 0)
    let hAxis = new THREE.Vector3().crossVectors(up, broadside).normalize()
    if (hAxis.length() < 0.01) {
      hAxis = new THREE.Vector3(1, 0, 0)
    }
    const vAxis = new THREE.Vector3().crossVectors(broadside, hAxis).normalize()

    const lambda = 3e8 / freqHz
    const dH = config.d_h_wavelengths * lambda
    const dV = config.d_v_wavelengths * lambda

    for (let iv = 0; iv < config.n_v; iv++) {
      for (let ih = 0; ih < config.n_h; ih++) {
        const oh = (ih - (config.n_h - 1) / 2) * dH
        const ov = (iv - (config.n_v - 1) / 2) * dV
        positions.push(
          new THREE.Vector3()
            .addScaledVector(hAxis, oh)
            .addScaledVector(vAxis, ov)
        )
      }
    }
    return positions
  }, [config.n_h, config.n_v, config.d_h_wavelengths, config.d_v_wavelengths, config.broadside, freqHz])

  // Update instanced mesh transforms
  useEffect(() => {
    if (!meshRef.current) return
    const dummy = new THREE.Object3D()
    for (let i = 0; i < localPositions.length; i++) {
      dummy.position.copy(localPositions[i])
      dummy.updateMatrix()
      meshRef.current.setMatrixAt(i, dummy.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  }, [localPositions])

  // Scale element radius to fit within spacing (don't overlap)
  const lambda = 3e8 / freqHz
  const minSpacing = Math.min(config.d_h_wavelengths, config.d_v_wavelengths) * lambda
  const elementRadius = Math.max(MIN_ELEMENT_RADIUS, Math.min(MAX_ELEMENT_RADIUS, minSpacing * 0.35))

  const sphereGeo = useMemo(
    () => new THREE.SphereGeometry(elementRadius, 12, 12),
    [elementRadius]
  )

  // Backplane dimensions: covers the full array extent plus a small margin
  const panelSize = useMemo(() => {
    const dH = config.d_h_wavelengths * lambda
    const dV = config.d_v_wavelengths * lambda
    const w = (config.n_h - 1) * dH + elementRadius * 4
    const h = (config.n_v - 1) * dV + elementRadius * 4
    // Ensure a visible minimum size
    return { w: Math.max(w, 0.05), h: Math.max(h, 0.05) }
  }, [config.n_h, config.n_v, config.d_h_wavelengths, config.d_v_wavelengths, lambda, elementRadius])

  const poleHeight = config.position[1]

  const arrowDir = useMemo(
    () => new THREE.Vector3(...config.broadside).normalize(),
    [config.broadside],
  )

  // Rotation to orient the backplane perpendicular to broadside
  const panelRotation = useMemo(() => {
    const q = new THREE.Quaternion()
    // PlaneGeometry faces +Z by default; rotate so it faces along broadside
    q.setFromUnitVectors(new THREE.Vector3(0, 0, 1), arrowDir)
    const e = new THREE.Euler().setFromQuaternion(q)
    return e
  }, [arrowDir])

  return (
    <group position={config.position}>
      {/* Backplane panel */}
      <mesh rotation={panelRotation}>
        <planeGeometry args={[panelSize.w, panelSize.h]} />
        <meshStandardMaterial color="#555555" side={THREE.DoubleSide} metalness={0.5} roughness={0.3} />
      </mesh>

      {/* Antenna elements */}
      <instancedMesh ref={meshRef} args={[sphereGeo, undefined, nElements]}>
        <meshStandardMaterial color={ELEMENT_COLOR} emissive={ELEMENT_COLOR} emissiveIntensity={0.3} />
      </instancedMesh>

      {/* Support pole */}
      {poleHeight > 0 && (
        <mesh position={[0, -poleHeight / 2, 0]}>
          <cylinderGeometry args={[POLE_RADIUS, POLE_RADIUS, poleHeight, 8]} />
          <meshStandardMaterial color={POLE_COLOR} />
        </mesh>
      )}

      {/* Broadside direction arrow */}
      <arrowHelper
        args={[arrowDir, new THREE.Vector3(0, 0, 0), 0.4, ARROW_COLOR.getHex(), 0.1, 0.06]}
      />
    </group>
  )
}
