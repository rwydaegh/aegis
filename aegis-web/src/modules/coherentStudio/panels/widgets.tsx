import type { ReactNode } from 'react'

// Shared presentational primitives for the studio control surface. Inline-styled
// to match the exposureLab panels (no Tailwind dependency, no semicolons).

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '6px 8px',
  fontSize: 12,
  background: '#16161d',
  color: '#ccc',
  border: '1px solid #2a2a35',
  borderRadius: 4,
}

/** A titled group with a thin divider, used to chunk the panel into sections. */
export function Group({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <div style={{ margin: '18px 0 0' }}>
      <h2 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.5, color: '#7a8', margin: '0 0 8px' }}>
        {title}
      </h2>
      {hint && <p style={{ fontSize: 11, color: '#666', margin: '0 0 8px' }}>{hint}</p>}
      {children}
    </div>
  )
}

/** A small field label above a control. */
export function FieldLabel({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <div style={{ fontSize: 12, color: '#9cf', margin: '10px 0 2px' }} title={title}>
      {children}
    </div>
  )
}

export interface Option<T> {
  value: T
  label: string
  disabled?: boolean
  hint?: string
}

/** A native select bound to a string/number value. */
export function LabeledSelect<T extends string | number>({
  value,
  options,
  onChange,
  parse,
  title,
}: {
  value: T
  options: Option<T>[]
  onChange: (v: T) => void
  /** Convert the raw string option value back to T (default: identity string). */
  parse?: (raw: string) => T
  title?: string
}) {
  return (
    <select
      value={String(value)}
      title={title}
      onChange={(e) => onChange(parse ? parse(e.target.value) : (e.target.value as T))}
      style={selectStyle}
    >
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)} disabled={o.disabled}>
          {o.label}
          {o.disabled && o.hint ? ` (${o.hint})` : ''}
        </option>
      ))}
    </select>
  )
}

/** A horizontal segmented control (one row of toggle buttons). */
export function Segmented<T extends string | number>({
  value,
  options,
  onChange,
}: {
  value: T
  options: Option<T>[]
  onChange: (v: T) => void
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${options.length}, 1fr)`, gap: 6 }}>
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={String(o.value)}
            type="button"
            disabled={o.disabled}
            title={o.disabled ? o.hint : undefined}
            onClick={() => !o.disabled && onChange(o.value)}
            style={{
              padding: '6px 4px',
              fontSize: 12,
              borderRadius: 4,
              border: '1px solid #2a2a35',
              cursor: o.disabled ? 'not-allowed' : 'pointer',
              opacity: o.disabled ? 0.4 : 1,
              background: active ? '#2a3a55' : '#16161d',
              color: active ? '#9cf' : '#ccc',
            }}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/**
 * A discrete stepper over an ordered list of values, rendered as a range input.
 * The slider rides the option index so non-uniform spacings (4, 8, 16, 40 cm)
 * stay evenly clickable.
 */
export function DiscreteSlider<T>({
  value,
  options,
  labelOf,
  onChange,
}: {
  value: T
  options: readonly T[]
  labelOf: (v: T) => string
  onChange: (v: T) => void
}) {
  const idx = Math.max(0, options.indexOf(value))
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
      <input
        type="range"
        min={0}
        max={options.length - 1}
        step={1}
        value={idx}
        onChange={(e) => onChange(options[parseInt(e.target.value, 10)])}
        style={{ flex: 1 }}
      />
      <span style={{ width: 56, textAlign: 'right', color: '#aaa', fontVariantNumeric: 'tabular-nums' }}>
        {labelOf(value)}
      </span>
    </label>
  )
}
