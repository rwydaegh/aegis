import type { ParamCap } from './capabilities'
import { isDisabled, disabledText } from './capabilities'

const hintClass = 'text-[10px] text-muted-foreground/60 ml-1'

export function Row({ cap, children }: { cap: ParamCap; children: React.ReactNode }) {
  const disabled = isDisabled(cap)
  return (
    <div className={disabled ? 'opacity-40 pointer-events-none' : ''}>
      {children}
    </div>
  )
}

export function Hint({ cap }: { cap: ParamCap }) {
  const text = disabledText(cap)
  if (!text) return null
  return <span className={hintClass}>{text}</span>
}

export function CheckboxRow({
  cap,
  label,
  checked,
  onChange,
  indent,
}: {
  cap: ParamCap
  label: string
  checked: boolean
  onChange: (v: boolean) => void
  indent?: boolean
}) {
  const disabled = isDisabled(cap)
  // For fixed "on" values, show checked even if store value differs
  const displayChecked = cap.kind === 'fixed' && cap.value === 'on' ? true : checked

  return (
    <div className={`${disabled ? 'opacity-40 pointer-events-none' : ''} ${indent ? 'ml-5' : ''}`}>
      <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer select-none">
        <input
          type="checkbox"
          className="rounded border-border accent-primary h-3.5 w-3.5"
          checked={displayChecked}
          onChange={e => onChange(e.target.checked)}
          disabled={disabled}
        />
        <span>{label}</span>
        <Hint cap={cap} />
      </label>
    </div>
  )
}
