import { useEffect, useState } from 'react'
import * as Sentry from '@sentry/react'
import { isClientError } from '@/api/client'
import { useLabStore } from '../store'
import { getPresets } from '../api'
import { CURATED_JOINTS } from '../lbs'

const PRESET_LABELS: Record<string, string> = {
  t_pose: 'T-pose',
  arms_down: 'Arms down',
  hand_to_cheek: 'Hand to cheek',
  arm_raised_front: 'Arm raised (front)',
}

const PRESET_ORDER = ['t_pose', 'arms_down', 'hand_to_cheek', 'arm_raised_front']

const AXIS_LABELS = ['x', 'y', 'z']

const BETA_LABELS: Record<number, string> = {
  0: 'Height',
  1: 'Build',
}

function Slider({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  onChange: (v: number) => void
}) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, margin: '4px 0' }}>
      <span style={{ width: 48, color: '#888' }}>{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={0.01}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ flex: 1 }}
      />
      <span style={{ width: 40, textAlign: 'right', color: '#aaa', fontVariantNumeric: 'tabular-nums' }}>
        {value.toFixed(2)}
      </span>
    </label>
  )
}

export default function PosePanel() {
  const pose = useLabStore(s => s.pose)
  const setPose = useLabStore(s => s.setPose)
  const setPreset = useLabStore(s => s.setPreset)
  const preset = useLabStore(s => s.preset)
  const selectedJoint = useLabStore(s => s.selectedJoint)
  const setSelectedJoint = useLabStore(s => s.setSelectedJoint)
  const betas = useLabStore(s => s.betas)
  const setBetas = useLabStore(s => s.setBetas)

  const [presets, setPresets] = useState<Record<string, number[]>>({})

  useEffect(() => {
    let cancelled = false
    getPresets()
      .then(p => {
        if (!cancelled) setPresets(p)
      })
      .catch(err => {
        if (cancelled) return
        if (!isClientError(err)) Sentry.captureException(err)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const applyPreset = (name: string) => {
    const p = presets[name]
    if (!p) return
    setPose([...p])
    setPreset(name)
  }

  const setPoseAxis = (joint: number, axis: number, value: number) => {
    const next = pose.slice()
    next[joint * 3 + axis] = value
    setPose(next)
  }

  const setBeta = (idx: number, value: number) => {
    const next = betas.slice()
    next[idx] = value
    setBetas(next)
  }

  const selectedLabel =
    selectedJoint == null ? null : CURATED_JOINTS.find(j => j.index === selectedJoint)?.label

  return (
    <div>
      <h2 style={{ fontSize: 14, margin: '16px 0 8px' }}>Presets</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
        {PRESET_ORDER.map(name => (
          <button
            key={name}
            onClick={() => applyPreset(name)}
            disabled={!presets[name]}
            style={{
              padding: '6px 8px',
              fontSize: 12,
              cursor: presets[name] ? 'pointer' : 'default',
              borderRadius: 4,
              border: '1px solid #2a2a35',
              background: preset === name ? '#2a3a55' : '#16161d',
              color: preset === name ? '#9cf' : '#ccc',
            }}
          >
            {PRESET_LABELS[name] ?? name}
          </button>
        ))}
      </div>

      <h2 style={{ fontSize: 14, margin: '20px 0 8px' }}>Joints</h2>
      <select
        value={selectedJoint ?? ''}
        onChange={e => setSelectedJoint(e.target.value === '' ? null : parseInt(e.target.value, 10))}
        style={{
          width: '100%',
          padding: '6px 8px',
          fontSize: 12,
          background: '#16161d',
          color: '#ccc',
          border: '1px solid #2a2a35',
          borderRadius: 4,
        }}
      >
        <option value="">Select a joint...</option>
        {CURATED_JOINTS.map(({ index, label }) => (
          <option key={index} value={index}>
            {label}
          </option>
        ))}
      </select>

      {selectedJoint != null && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 12, color: '#9cf', marginBottom: 4 }}>{selectedLabel}</div>
          {AXIS_LABELS.map((axisLabel, axis) => (
            <Slider
              key={axis}
              label={axisLabel}
              value={pose[selectedJoint * 3 + axis] ?? 0}
              min={-Math.PI}
              max={Math.PI}
              onChange={v => setPoseAxis(selectedJoint, axis, v)}
            />
          ))}
        </div>
      )}

      <h2 style={{ fontSize: 14, margin: '20px 0 8px' }}>Shape</h2>
      {[0, 1].map(idx => (
        <Slider
          key={idx}
          label={BETA_LABELS[idx] ?? `b${idx}`}
          value={betas[idx] ?? 0}
          min={-3}
          max={3}
          onChange={v => setBeta(idx, v)}
        />
      ))}
    </div>
  )
}
