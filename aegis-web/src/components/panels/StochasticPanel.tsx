import { useEffect, useState } from 'react'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'

interface PresetInfo {
  name: string
  featured: boolean
  params: Record<string, number | string>
}

export default function StochasticPanel() {
  const pathSource = useSceneStore(s => s.pathSource)
  const setPathSource = useSceneStore(s => s.setPathSource)
  const preset = useSimulationStore(s => s.stochasticPreset)
  const setPreset = useSimulationStore(s => s.setStochasticPreset)
  const overrides = useSimulationStore(s => s.stochasticOverrides)
  const setOverrides = useSimulationStore(s => s.setStochasticOverrides)
  const seed = useSimulationStore(s => s.stochasticSeed)
  const setSeed = useSimulationStore(s => s.setStochasticSeed)

  const [presets, setPresets] = useState<PresetInfo[]>([])
  const [presetParams, setPresetParams] = useState<Record<string, number | string>>({})

  const enabled = pathSource === 'stochastic'

  useEffect(() => {
    fetch('/api/channel-presets')
      .then(r => r.json())
      .then((data: PresetInfo[]) => {
        setPresets(data.filter(p => p.featured))
        const current = data.find(p => p.name === preset)
        if (current) setPresetParams(current.params)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    const p = presets.find(p => p.name === preset)
    if (p) setPresetParams(p.params)
  }, [preset, presets])

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const inputClass = selectClass
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"

  const getVal = (key: string, fallback: number = 0) =>
    overrides[key] ?? (presetParams[key] as number) ?? fallback

  const setOverride = (key: string, val: number) =>
    setOverrides({ ...overrides, [key]: val })

  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-foreground">
        <input type="checkbox" checked={enabled}
          onChange={e => setPathSource(e.target.checked ? 'stochastic' : 'synthetic')} />
        Enable stochastic channel
      </label>

      {enabled && (
        <>
          <label className={labelClass}>Scenario</label>
          <select className={selectClass} value={preset}
            onChange={e => { setPreset(e.target.value); setOverrides({}) }}>
            {presets.map(p => (
              <option key={p.name} value={p.name}>
                {p.name.replace(/_/g, ' ').replace('3GPP ', '')}
              </option>
            ))}
          </select>

          <label className={labelClass}>K-factor (dB)</label>
          <input type="number" className={inputClass} step={1}
            value={getVal('KF_mu', 9)}
            onChange={e => setOverride('KF_mu', Number(e.target.value))} />

          <label className={labelClass}>Azimuth spread (deg)</label>
          <input type="number" className={inputClass} step={1} min={1} max={180}
            value={Math.round(10 ** getVal('AS_A_mu', 1.73))}
            onChange={e => {
              const deg = Number(e.target.value)
              if (deg > 0) setOverride('AS_A_mu', Math.log10(deg))
            }} />

          <label className={labelClass}>Elevation spread (deg)</label>
          <input type="number" className={inputClass} step={1} min={1} max={90}
            value={Math.round(10 ** getVal('ES_A_mu', 0.73))}
            onChange={e => {
              const deg = Number(e.target.value)
              if (deg > 0) setOverride('ES_A_mu', Math.log10(deg))
            }} />

          <label className={labelClass}>Clusters</label>
          <input type="number" className={inputClass} step={1} min={1} max={50}
            value={getVal('NumClusters', 12)}
            onChange={e => setOverride('NumClusters', Number(e.target.value))} />

          <label className={labelClass}>Sub-paths per cluster</label>
          <input type="number" className={inputClass} step={1} min={1} max={20}
            value={getVal('NumSubPaths', 20)}
            onChange={e => setOverride('NumSubPaths', Number(e.target.value))} />

          <label className={labelClass}>Seed</label>
          <input type="number" className={inputClass}
            value={seed} onChange={e => setSeed(Number(e.target.value))} />

          <button
            className="mt-2 text-xs text-primary hover:underline cursor-pointer"
            onClick={() => setOverrides({})}
          >
            Reset to preset defaults
          </button>
        </>
      )}
    </div>
  )
}
