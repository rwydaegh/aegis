export default function CorrectionToggle({
  label,
  checked,
  onChange,
  disabled,
  title,
}: {
  label: string
  checked: boolean
  onChange: (on: boolean) => void
  disabled?: boolean
  title?: string
}) {
  return (
    <label
      className={`flex items-center gap-2 text-xs cursor-pointer select-none ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
      title={title}
    >
      <input
        type="checkbox"
        className="rounded border-border accent-primary h-3.5 w-3.5"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span className="text-foreground">{label}</span>
    </label>
  )
}
