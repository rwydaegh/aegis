import { useState, useEffect } from 'react'
import { useAntennaStore, type AntennaArrayConfig } from '@/stores/antenna'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import type { ElementPattern } from '@/api/types'
import Tex from '@/components/ui/Tex'

/** Number input that allows clearing the field while typing, commits on blur. */
function NumInput({
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

const PATTERN_OPTIONS: { value: ElementPattern; label: string }[] = [
  { value: 'short_dipole', label: 'Dipole' },
  { value: 'patch', label: 'Patch' },
  { value: 'isotropic', label: 'Iso' },
]

export default function AntennasPanel() {
  const mimoEnabled = useMIMOStore(s => s.enabled)

  const antennas = useAntennaStore(s => s.antennas)
  const selectedId = useAntennaStore(s => s.selectedId)
  const addAntenna = useAntennaStore(s => s.addAntenna)
  const removeAntenna = useAntennaStore(s => s.removeAntenna)
  const updateAntenna = useAntennaStore(s => s.updateAntenna)
  const selectAntenna = useAntennaStore(s => s.selectAntenna)
  const setEnabled = useAntennaStore(s => s.setEnabled)

  const freqGhz = useSimulationStore(s => s.freqGhz)

  if (mimoEnabled) {
    return (
      <p className="text-xs text-muted-foreground">
        MIMO mode active. Antenna config is managed in the MIMO and Antenna tabs.
      </p>
    )
  }

  const antennaList = [...antennas.values()]
  const selected = selectedId ? antennas.get(selectedId) ?? null : null
  const lambda_m = 3e8 / (freqGhz * 1e9)

  const inputClass =
    'w-full bg-muted/50 border border-border rounded px-1.5 py-1 text-[11px] text-foreground font-mono'
  const labelClass = 'text-[10px] text-muted-foreground block mb-0.5'
  const sectionClass =
    'text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1'

  function updateSelected(partial: Partial<(typeof antennaList)[0]>) {
    if (!selectedId) return
    updateAntenna(selectedId, partial)
  }

  function updateArrayConfig(partial: Partial<AntennaArrayConfig>) {
    if (!selectedId || !selected) return
    updateAntenna(selectedId, { arrayConfig: { ...selected.arrayConfig, ...partial } })
  }

  return (
    <div className="space-y-3">
      {/* Antenna list */}
      <div className="space-y-1">
        {antennaList.length === 0 && (
          <p className="text-[11px] text-muted-foreground">No antennas. Click below to add one.</p>
        )}
        {antennaList.map(ant => {
          const isSelected = ant.id === selectedId
          const arraySize = ant.arrayConfig.n_h * ant.arrayConfig.n_v
          return (
            <div
              key={ant.id}
              className={`flex items-center gap-1.5 rounded px-1.5 py-1 cursor-pointer transition-colors ${
                isSelected
                  ? 'bg-primary/15 border border-primary/40'
                  : 'bg-muted/50 border border-transparent hover:bg-muted'
              }`}
              onClick={() => selectAntenna(ant.id)}
            >
              {/* Enable checkbox */}
              <input
                type="checkbox"
                className="rounded border-border accent-primary h-3 w-3 shrink-0"
                checked={ant.enabled}
                onChange={e => {
                  e.stopPropagation()
                  setEnabled(ant.id, e.target.checked)
                }}
                onClick={e => e.stopPropagation()}
              />

              {/* Name */}
              <span className="text-[11px] text-foreground flex-1 truncate">{ant.name}</span>

              {/* Array size badge */}
              {arraySize > 1 && (
                <span className="text-[9px] text-muted-foreground bg-muted rounded px-1 py-0.5 shrink-0">
                  {ant.arrayConfig.n_h}x{ant.arrayConfig.n_v}
                </span>
              )}

              {/* Position */}
              <span className="text-[9px] text-muted-foreground/70 font-mono shrink-0">
                ({ant.position[0].toFixed(1)}, {ant.position[1].toFixed(1)}, {ant.position[2].toFixed(1)})
              </span>

              {/* Delete button */}
              <button
                className="shrink-0 w-4 h-4 flex items-center justify-center rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                title="Remove antenna"
                onClick={e => {
                  e.stopPropagation()
                  removeAntenna(ant.id)
                }}
              >
                <svg
                  width="10"
                  height="10"
                  viewBox="0 0 10 10"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                >
                  <path d="M2 2l6 6M8 2l-6 6" />
                </svg>
              </button>
            </div>
          )
        })}
      </div>

      {/* Add button */}
      <button
        className="w-full text-[11px] py-1.5 rounded border border-dashed border-border text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        onClick={() => addAntenna([5, 0, 0])}
      >
        + Add antenna
      </button>

      {/* Selected antenna config */}
      {selected && (
        <div className="space-y-3 pt-2 border-t border-border">
          {/* Power */}
          <div>
            <p className={sectionClass}>Power</p>
            <label className={labelClass}>
              <Tex math={'P_\\text{TX}'} />
            </label>
            <div className="flex gap-2 items-center">
              <div className="flex-1">
                <input
                  type="number"
                  className={inputClass}
                  value={selected.powerDbm}
                  onChange={e => {
                    const v = Number(e.target.value)
                    if (Number.isFinite(v)) updateSelected({ powerDbm: v })
                  }}
                  step={1}
                />
                <span className="text-[10px] text-muted-foreground mt-0.5 block">dBm</span>
              </div>
              <span className="text-muted-foreground text-xs pb-3">=</span>
              <div className="flex-1">
                <input
                  type="number"
                  className={inputClass}
                  value={Number((10 ** ((selected.powerDbm - 30) / 10)).toPrecision(4))}
                  onChange={e => {
                    const w = Number(e.target.value)
                    if (w > 0)
                      updateSelected({
                        powerDbm: Math.round((10 * Math.log10(w) + 30) * 100) / 100,
                      })
                  }}
                  step={0.1}
                  min={0}
                />
                <span className="text-[10px] text-muted-foreground mt-0.5 block">W</span>
              </div>
            </div>
          </div>

          {/* Array size */}
          <div>
            <p className={sectionClass}>Array size</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelClass}>N_h</label>
                <NumInput
                  className={inputClass}
                  value={selected.arrayConfig.n_h}
                  min={1} max={16} step={1} integer
                  onChange={v => updateArrayConfig({ n_h: v })}
                />
              </div>
              <div>
                <label className={labelClass}>N_v</label>
                <NumInput
                  className={inputClass}
                  value={selected.arrayConfig.n_v}
                  min={1} max={16} step={1} integer
                  onChange={v => updateArrayConfig({ n_v: v })}
                />
              </div>
            </div>
          </div>

          {/* Element spacing */}
          <div>
            <p className={sectionClass}>Element spacing</p>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelClass}>d_h (wavelengths)</label>
                <NumInput
                  className={inputClass}
                  value={selected.arrayConfig.d_h_wavelengths}
                  min={0.1} max={2.0} step={0.1}
                  onChange={v => updateArrayConfig({ d_h_wavelengths: v })}
                />
              </div>
              <div>
                <label className={labelClass}>d_v (wavelengths)</label>
                <NumInput
                  className={inputClass}
                  value={selected.arrayConfig.d_v_wavelengths}
                  min={0.1} max={2.0} step={0.1}
                  onChange={v => updateArrayConfig({ d_v_wavelengths: v })}
                />
              </div>
            </div>
            <p className="text-[9px] text-muted-foreground/60 mt-1">
              {(selected.arrayConfig.d_h_wavelengths * lambda_m * 1000).toFixed(1)} mm x{' '}
              {(selected.arrayConfig.d_v_wavelengths * lambda_m * 1000).toFixed(1)} mm at{' '}
              {freqGhz} GHz
            </p>
          </div>

          {/* Element pattern */}
          <div>
            <p className={sectionClass}>Element pattern</p>
            <div className="flex gap-1">
              {PATTERN_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => updateArrayConfig({ element_pattern: opt.value })}
                  className={`flex-1 text-[10px] py-1 px-1.5 rounded border transition-colors ${
                    selected.arrayConfig.element_pattern === opt.value
                      ? 'bg-primary/15 border border-primary/40'
                      : 'bg-muted/50 border border-transparent hover:bg-muted'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Position */}
          <div>
            <p className={sectionClass}>Position</p>
            <div className="flex gap-1">
              {(['X', 'Y', 'Z'] as const).map((axis, i) => (
                <label key={axis} className="flex items-center gap-0.5 flex-1">
                  <span className="text-[9px] text-muted-foreground">{axis}</span>
                  <input
                    type="number"
                    step={0.5}
                    value={selected.position[i]}
                    onChange={e => {
                      const v = parseFloat(e.target.value)
                      if (isNaN(v)) return
                      const pos: [number, number, number] = [...selected.position]
                      pos[i] = i === 1 ? Math.max(0, v) : v
                      updateSelected({ position: pos })
                    }}
                    className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
                  />
                </label>
              ))}
            </div>
            <p className="text-[9px] text-muted-foreground/60 mt-0.5">Click scene to place</p>
          </div>

          {/* Height */}
          <div>
            <p className={sectionClass}>Height</p>
            <div className="flex items-center gap-2">
              <div className="flex-1">
                <NumInput
                  className={inputClass}
                  value={selected.height}
                  min={0.5}
                  max={50}
                  step={0.5}
                  onChange={v => {
                    if (selectedId) useAntennaStore.getState().setHeight(selectedId, v)
                  }}
                />
              </div>
              <span className="text-[10px] text-muted-foreground">m</span>
            </div>
          </div>

          {/* Direction */}
          <div>
            <p className={sectionClass}>Direction</p>
            {(() => {
              const [bx, by, bz] = selected.arrayConfig.broadside
              const horLen = Math.sqrt(bx * bx + bz * bz)
              const azDeg = Math.atan2(bx, -bz) * (180 / Math.PI)
              const tiltDeg = Math.atan2(-by, horLen) * (180 / Math.PI)

              const setBroadside = (newBs: [number, number, number]) => {
                if (!selectedId) return
                updateAntenna(selectedId, {
                  focusPoint: null,
                  arrayConfig: { ...selected.arrayConfig, broadside: newBs },
                })
              }

              return (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className={labelClass}>Azimuth</label>
                    <NumInput
                      className={inputClass}
                      value={Math.round(azDeg * 10) / 10}
                      min={-180}
                      max={180}
                      step={5}
                      onChange={v => {
                        const azRad = v * Math.PI / 180
                        const tiltRad = tiltDeg * Math.PI / 180
                        const cosTilt = Math.cos(tiltRad)
                        setBroadside([
                          Math.sin(azRad) * cosTilt,
                          -Math.sin(tiltRad),
                          -Math.cos(azRad) * cosTilt,
                        ])
                      }}
                    />
                    <span className="text-[10px] text-muted-foreground mt-0.5 block">deg</span>
                  </div>
                  <div>
                    <label className={labelClass}>Tilt</label>
                    <NumInput
                      className={inputClass}
                      value={Math.round(tiltDeg * 10) / 10}
                      min={-90}
                      max={90}
                      step={1}
                      onChange={v => {
                        const azRad = azDeg * Math.PI / 180
                        const tiltRad = v * Math.PI / 180
                        const cosTilt = Math.cos(tiltRad)
                        setBroadside([
                          Math.sin(azRad) * cosTilt,
                          -Math.sin(tiltRad),
                          -Math.cos(azRad) * cosTilt,
                        ])
                      }}
                    />
                    <span className="text-[10px] text-muted-foreground mt-0.5 block">deg (+down)</span>
                  </div>
                </div>
              )
            })()}
          </div>

          {/* Focus point (patch only) */}
          {selected.arrayConfig.element_pattern === 'patch' && (
            <div>
              <p className={sectionClass}>Focus point</p>
              <div className="flex gap-1">
                {(['X', 'Y', 'Z'] as const).map((axis, i) => (
                  <label key={axis} className="flex items-center gap-0.5 flex-1">
                    <span className="text-[9px] text-muted-foreground">{axis}</span>
                    <input
                      type="number"
                      step={0.5}
                      value={selected.focusPoint?.[i] ?? 0}
                      onChange={e => {
                        const v = parseFloat(e.target.value)
                        if (isNaN(v)) return
                        const fp: [number, number, number] = selected.focusPoint
                          ? [...selected.focusPoint] as [number, number, number]
                          : [0, 0, 0]
                        fp[i] = v
                        if (selectedId) useAntennaStore.getState().setFocusPoint(selectedId, fp)
                      }}
                      className="w-full bg-muted/50 border border-border rounded px-1 py-0.5 text-[10px] text-foreground font-mono"
                    />
                  </label>
                ))}
              </div>
              <p className="text-[9px] text-muted-foreground/60 mt-0.5">Target for broadside direction</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
