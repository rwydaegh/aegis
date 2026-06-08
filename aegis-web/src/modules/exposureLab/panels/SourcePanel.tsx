import { useEffect, useState } from 'react'
import * as Sentry from '@sentry/react'
import { useLabStore } from '../store'
import { getNfPatterns, type LabPattern } from '../api'

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  fontSize: 12,
  background: '#16161d',
  color: '#ccc',
  border: '1px solid #2a2a35',
  borderRadius: 4,
}

function Slider({
  label,
  value,
  min,
  max,
  step = 0.01,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (v: number) => void
}) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, margin: '4px 0' }}>
      <span style={{ width: 56, color: '#888' }}>{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ flex: 1 }}
      />
      <span style={{ width: 44, textAlign: 'right', color: '#aaa', fontVariantNumeric: 'tabular-nums' }}>
        {value.toFixed(2)}
      </span>
    </label>
  )
}

export default function SourcePanel() {
  const sourceMode = useLabStore((s) => s.sourceMode)
  const setSourceMode = useLabStore((s) => s.setSourceMode)

  // near
  const patternId = useLabStore((s) => s.patternId)
  const setPatternId = useLabStore((s) => s.setPatternId)
  const phonePos = useLabStore((s) => s.phonePos)
  const setPhonePos = useLabStore((s) => s.setPhonePos)
  const yaw = useLabStore((s) => s.yaw)
  const setYaw = useLabStore((s) => s.setYaw)
  const pitch = useLabStore((s) => s.pitch)
  const setPitch = useLabStore((s) => s.setPitch)
  const roll = useLabStore((s) => s.roll)
  const setRoll = useLabStore((s) => s.setRoll)
  const powerW = useLabStore((s) => s.powerW)
  const setPowerW = useLabStore((s) => s.setPowerW)

  // far
  const thetaInc = useLabStore((s) => s.thetaInc)
  const setThetaInc = useLabStore((s) => s.setThetaInc)
  const phiInc = useLabStore((s) => s.phiInc)
  const setPhiInc = useLabStore((s) => s.setPhiInc)
  const polAngle = useLabStore((s) => s.polAngle)
  const setPolAngle = useLabStore((s) => s.setPolAngle)

  const [patterns, setPatterns] = useState<LabPattern[]>([])

  useEffect(() => {
    let cancelled = false
    getNfPatterns()
      .then((p) => {
        if (!cancelled) setPatterns(p)
      })
      .catch((err) => {
        if (!cancelled) Sentry.captureException(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const setPosAxis = (axis: number, value: number) => {
    const next = phonePos.slice() as [number, number, number]
    next[axis] = value
    setPhonePos(next)
  }

  return (
    <div>
      <h2 style={{ fontSize: 14, margin: '16px 0 8px' }}>Source</h2>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 12 }}>
        {(['near', 'far'] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setSourceMode(mode)}
            style={{
              padding: '6px 8px',
              fontSize: 12,
              cursor: 'pointer',
              borderRadius: 4,
              border: '1px solid #2a2a35',
              background: sourceMode === mode ? '#2a3a55' : '#16161d',
              color: sourceMode === mode ? '#9cf' : '#ccc',
            }}
          >
            {mode === 'near' ? 'Near field (phone)' : 'Far field (plane wave)'}
          </button>
        ))}
      </div>

      {sourceMode === 'near' && (
        <div>
          <div style={{ fontSize: 12, color: '#888', margin: '4px 0' }}>Pattern</div>
          <select value={patternId} onChange={(e) => setPatternId(e.target.value)} style={selectStyle}>
            {patterns.length === 0 && <option value={patternId}>{patternId}</option>}
            {patterns.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>

          <div style={{ fontSize: 12, color: '#9cf', margin: '12px 0 2px' }}>Position (m)</div>
          <Slider label="x" value={phonePos[0]} min={-0.6} max={0.6} onChange={(v) => setPosAxis(0, v)} />
          <Slider label="y" value={phonePos[1]} min={-0.6} max={0.6} onChange={(v) => setPosAxis(1, v)} />
          <Slider label="z" value={phonePos[2]} min={-0.6} max={0.6} onChange={(v) => setPosAxis(2, v)} />

          <div style={{ fontSize: 12, color: '#9cf', margin: '12px 0 2px' }}>Orientation (rad)</div>
          <Slider label="yaw" value={yaw} min={-Math.PI} max={Math.PI} onChange={setYaw} />
          <Slider label="pitch" value={pitch} min={-Math.PI} max={Math.PI} onChange={setPitch} />
          <Slider label="roll" value={roll} min={-Math.PI} max={Math.PI} onChange={setRoll} />

          <div style={{ fontSize: 12, color: '#9cf', margin: '12px 0 2px' }}>Radiated power (W)</div>
          <Slider label="power" value={powerW} min={0.1} max={5} step={0.05} onChange={setPowerW} />
        </div>
      )}

      {sourceMode === 'far' && (
        <div>
          <div style={{ fontSize: 12, color: '#9cf', margin: '12px 0 2px' }}>Incidence (rad)</div>
          <Slider label="theta" value={thetaInc} min={0} max={Math.PI} onChange={setThetaInc} />
          <Slider label="phi" value={phiInc} min={-Math.PI} max={Math.PI} onChange={setPhiInc} />
          <div style={{ fontSize: 12, color: '#9cf', margin: '12px 0 2px' }}>Polarisation (rad)</div>
          <Slider label="pol" value={polAngle} min={0} max={Math.PI} onChange={setPolAngle} />
        </div>
      )}
    </div>
  )
}
