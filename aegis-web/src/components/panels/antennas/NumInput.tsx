import { useState, useEffect } from 'react'

/** Number input that allows clearing the field while typing, commits on blur. */
export function NumInput({
  value,
  onChange,
  min,
  max,
  step,
  integer,
  className,
}: {
  value: number
  onChange: (v: number) => void
  min?: number
  max?: number
  step?: number
  integer?: boolean
  className?: string
}) {
  const [local, setLocal] = useState(String(value))
  useEffect(() => setLocal(String(value)), [value])

  return (
    <input
      type="number"
      className={className}
      value={local}
      min={min}
      max={max}
      step={step}
      onChange={e => {
        setLocal(e.target.value)
        const v = integer ? parseInt(e.target.value) : parseFloat(e.target.value)
        if (!isNaN(v) && (min == null || v >= min) && (max == null || v <= max)) {
          onChange(v)
        }
      }}
      onBlur={() => {
        const v = integer ? parseInt(local) : parseFloat(local)
        if (isNaN(v) || (min != null && v < min)) {
          setLocal(String(value))
        } else if (max != null && v > max) {
          setLocal(String(max))
          onChange(max)
        }
      }}
    />
  )
}
