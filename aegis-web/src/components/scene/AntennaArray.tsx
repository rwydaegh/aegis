import { useMemo, useRef, useEffect } from 'react'
import * as THREE from 'three'
import type { ArrayConfig } from '@/api/types'

interface AntennaArrayProps {
  config: ArrayConfig
  freqHz: number
}

const ELEMENT_RADIUS = 0.03
const ELEMENT_COLOR = new THREE.Color(0.8, 0.2, 0.2)
const POLE_RADIUS = 0.04
const POLE_COLOR = new THREE.Color(0.4, 0.4, 0.4)
const ARROW_COLOR = new THREE.Color(1, 0.4, 0)

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

  const sphereGeo = useMemo(() => new THREE.SphereGeometry(ELEMENT_RADIUS, 8, 8), [])

  const poleHeight = config.position[1]

  const arrowDir = useMemo(
    () => new THREE.Vector3(...config.broadside).normalize(),
    [config.broadside],
  )

  return (
    <group position={config.position}>
      <instancedMesh ref={meshRef} args={[sphereGeo, undefined, nElements]}>
        <meshStandardMaterial color={ELEMENT_COLOR} />
      </instancedMesh>

      {poleHeight > 0 && (
        <mesh position={[0, -poleHeight / 2, 0]}>
          <cylinderGeometry args={[POLE_RADIUS, POLE_RADIUS, poleHeight, 8]} />
          <meshStandardMaterial color={POLE_COLOR} />
        </mesh>
      )}

      <arrowHelper
        args={[arrowDir, new THREE.Vector3(0, 0, 0), 0.5, ARROW_COLOR.getHex(), 0.15, 0.08]}
      />
    </group>
  )
}
