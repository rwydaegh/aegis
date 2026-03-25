import { useMIMOStore } from '@/stores/mimo'
import { useSimulationStore } from '@/stores/simulation'
import type { ElementPattern } from '@/api/types'

const PATTERN_OPTIONS: { value: ElementPattern; label: string; desc: string }[] = [
  { value: 'patch', label: 'Patch', desc: 'Directional cos^q(theta) pattern' },
  { value: 'isotropic', label: 'Isotropic', desc: 'Omnidirectional' },
]

export default function AntennaPanel() {
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const arrayConfig = useMIMOStore(s => s.arrayConfig)
  const setArrayConfig = useMIMOStore(s => s.setArrayConfig)
  const freqGhz = useSimulationStore(s => s.freqGhz)

  if (!mimoEnabled || !arrayConfig) {
    return (
      <p className="text-xs text-muted-foreground">
        Enable MIMO mode to configure the antenna array.
      </p>
    )
  }

  const lambda_m = 3e8 / (freqGhz * 1e9)
  const nElements = arrayConfig.n_h * arrayConfig.n_v

  const inputClass = "w-full bg-muted/50 border border-border rounded px-1.5 py-1 text-[11px] text-foreground font-mono"
  const labelClass = "text-[10px] text-muted-foreground block mb-0.5"

  const update = (partial: Partial<typeof arrayConfig>) => {
    setArrayConfig({ ...arrayConfig, ...partial })
  }

  return (
    <div className="space-y-3">
      {/* Array size */}
      <div>
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
          Array size
        </p>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className={labelClass}>Columns (N_h)</label>
            <input
              type="number"
              className={inputClass}
              value={arrayConfig.n_h}
              min={1} max={16} step={1}
              onChange={e => {
                const v = parseInt(e.target.value)
                if (!isNaN(v) && v >= 1 && v <= 16) update({ n_h: v })
              }}
            />
          </div>
          <div>
            <label className={labelClass}>Rows (N_v)</label>
            <input
              type="number"
              className={inputClass}
              value={arrayConfig.n_v}
              min={1} max={16} step={1}
              onChange={e => {
                const v = parseInt(e.target.value)
                if (!isNaN(v) && v >= 1 && v <= 16) update({ n_v: v })
              }}
            />
          </div>
        </div>
        <p className="text-[9px] text-muted-foreground/60 mt-1">
          {nElements} elements total
        </p>
      </div>

      {/* Spacing */}
      <div>
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
          Element spacing
        </p>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className={labelClass}>d_h (wavelengths)</label>
            <input
              type="number"
              className={inputClass}
              value={arrayConfig.d_h_wavelengths}
              min={0.1} max={2.0} step={0.1}
              onChange={e => {
                const v = parseFloat(e.target.value)
                if (!isNaN(v) && v > 0) update({ d_h_wavelengths: v })
              }}
            />
          </div>
          <div>
            <label className={labelClass}>d_v (wavelengths)</label>
            <input
              type="number"
              className={inputClass}
              value={arrayConfig.d_v_wavelengths}
              min={0.1} max={2.0} step={0.1}
              onChange={e => {
                const v = parseFloat(e.target.value)
                if (!isNaN(v) && v > 0) update({ d_v_wavelengths: v })
              }}
            />
          </div>
        </div>
        <p className="text-[9px] text-muted-foreground/60 mt-1">
          {(arrayConfig.d_h_wavelengths * lambda_m * 1000).toFixed(1)} mm x{' '}
          {(arrayConfig.d_v_wavelengths * lambda_m * 1000).toFixed(1)} mm at {freqGhz} GHz
        </p>
      </div>

      {/* Element pattern */}
      <div>
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
          Element pattern
        </p>
        <div className="flex gap-1">
          {PATTERN_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => update({ element_pattern: opt.value })}
              className={`flex-1 text-[10px] py-1 px-1.5 rounded border transition-colors ${
                arrayConfig.element_pattern === opt.value
                  ? 'bg-primary text-primary-foreground border-primary'
                  : 'bg-muted/50 text-muted-foreground border-border hover:bg-muted'
              }`}
              title={opt.desc}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Position */}
      <div>
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
          Position
        </p>
        <div className="flex gap-1">
          {(['X', 'Y', 'Z'] as const).map((axis, i) => (
            <label key={axis} className="flex items-center gap-0.5 flex-1">
              <span className="text-[9px] text-muted-foreground">{axis}</span>
              <input
                type="number"
                step={0.5}
                value={arrayConfig.position[i]}
                onChange={e => {
                  const v = parseFloat(e.target.value)
                  if (isNaN(v)) return
                  const pos: [number, number, number] = [...arrayConfig.position]
                  pos[i] = i === 1 ? Math.max(0, v) : v
                  update({ position: pos })
                }}
                className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
              />
            </label>
          ))}
        </div>
        <p className="text-[9px] text-muted-foreground/60 mt-0.5">Click scene to place</p>
      </div>
    </div>
  )
}
