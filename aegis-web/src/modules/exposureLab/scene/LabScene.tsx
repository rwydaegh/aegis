import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import PosableBody from './PosableBody'
import JointGizmo from './JointGizmo'
import RadiationLobe from './RadiationLobe'
import FarFieldRay from './FarFieldRay'
import SmartphoneModel from '@/components/scene/SmartphoneModel'
import { useLabStore } from '../store'

// Near-field phone + radiation lobe, grouped under one transform so the lobe
// rigidly follows the phone. The group rotation uses THREE Euler order 'ZYX'
// with [roll, pitch, yaw], which produces Rz(yaw)*Ry(pitch)*Rx(roll), matching
// the server's euler_to_matrix(yaw, pitch, roll) in nearfield/phone.py.
function NearFieldSource() {
  const phonePos = useLabStore((s) => s.phonePos)
  const yaw = useLabStore((s) => s.yaw)
  const pitch = useLabStore((s) => s.pitch)
  const roll = useLabStore((s) => s.roll)

  return (
    <group position={phonePos} rotation={[roll, pitch, yaw, 'ZYX']}>
      <SmartphoneModel position={[0, 0, 0]} orientation={[0, 0, 0]} />
      <RadiationLobe />
    </group>
  )
}

// Self-contained R3F scene for the Exposure Lab. Deliberately does NOT reuse
// SceneRoot (which is wired into the main viewer stores). The body renders in the
// RAW SMPL-X frame (pelvis at the origin, Y-up): head ~ +0.7 m, feet ~ -1.15 m.
// Keeping the display frame identical to the server frame lets the phone position
// pass straight through as source_pos for the self-shadow query (see PosableBody).
export default function LabScene() {
  const sourceMode = useLabStore((s) => s.sourceMode)
  return (
    <Canvas camera={{ position: [0, -0.2, 3.0], fov: 45 }} shadows>
      <color attach="background" args={['#0a0a0f']} />

      <ambientLight intensity={0.5} />
      <directionalLight position={[5, 10, 5]} intensity={0.9} castShadow />
      <hemisphereLight args={['#b1e1ff', '#2c2c2c', 0.3]} />

      {/* Floor grid at the feet (raw SMPL-X feet sit near y = -1.15). */}
      <gridHelper args={[10, 20, '#444444', '#222222']} position={[0, -1.15, 0]} />

      <PosableBody />
      <JointGizmo />

      {/* Source visuals: near-field phone lobe / far-field incidence ray. */}
      {sourceMode === 'near' && <NearFieldSource />}
      {sourceMode === 'far' && <FarFieldRay />}

      <OrbitControls makeDefault enableDamping target={[0, -0.2, 0]} />
    </Canvas>
  )
}
