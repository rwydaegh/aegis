import CorrectionToggle from '@/components/common/CorrectionToggle'
import { useLabStore } from '../store'
import type { LabDiffractionModel } from '../store'

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  fontSize: 12,
  background: '#16161d',
  color: '#ccc',
  border: '1px solid #2a2a35',
  borderRadius: 4,
}

const DIFFRACTION_OPTIONS: { value: LabDiffractionModel; label: string }[] = [
  { value: 'none', label: 'None' },
  { value: 'gelu', label: 'GeLU (knife edge)' },
  { value: 'fock', label: 'Fock (curved)' },
]

export default function PhysicsPanel() {
  const diffractionModel = useLabStore((s) => s.diffractionModel)
  const selfShadow = useLabStore((s) => s.selfShadow)
  const curvature = useLabStore((s) => s.curvature)
  const fresnel = useLabStore((s) => s.fresnel)
  const polarisation = useLabStore((s) => s.polarisation)
  const freqMhz = useLabStore((s) => s.freqMhz)
  const setPhysics = useLabStore((s) => s.setPhysics)
  const setFreqMhz = useLabStore((s) => s.setFreqMhz)

  return (
    <div>
      <h2 style={{ fontSize: 14, margin: '20px 0 8px' }}>Physics</h2>

      <div style={{ fontSize: 12, color: '#888', margin: '4px 0' }}>Diffraction model</div>
      <select
        value={diffractionModel}
        onChange={(e) => setPhysics({ diffractionModel: e.target.value as LabDiffractionModel })}
        style={selectStyle}
      >
        {DIFFRACTION_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, margin: '12px 0' }}>
        <CorrectionToggle
          label="Self-shadowing"
          checked={selfShadow}
          onChange={(on) => setPhysics({ selfShadow: on })}
          title="Distal self-shadowing: one body part shadows another; changes non-convex dose"
        />
        <CorrectionToggle
          label="Curvature"
          checked={curvature}
          onChange={(on) => setPhysics({ curvature: on })}
        />
        <CorrectionToggle
          label="Fresnel"
          checked={fresnel}
          onChange={(on) => setPhysics({ fresnel: on })}
        />
        <CorrectionToggle
          label="Polarisation"
          checked={polarisation}
          onChange={(on) => setPhysics({ polarisation: on })}
        />
      </div>

      <div style={{ fontSize: 12, color: '#888', margin: '4px 0' }}>
        Frequency (MHz): {freqMhz.toFixed(0)}
      </div>
      <input
        type="range"
        min={700}
        max={6000}
        step={10}
        value={freqMhz}
        onChange={(e) => setFreqMhz(parseFloat(e.target.value))}
        style={{ width: '100%' }}
      />

      <p style={{ fontSize: 11, color: '#666', margin: '12px 0 0' }}>
        Lab dose always runs in spatial mode.
      </p>
    </div>
  )
}
