import { useEffect, useMemo, useState } from 'react'
import * as Sentry from '@sentry/react'
import { useSceneStore } from '@/stores/scene'
import { useSimulationStore } from '@/stores/simulation'
import { useNotificationStore } from '@/stores/notifications'
import { LSP_KEYS, getLSPMeta } from '@/lib/lsp-labels'

interface PresetInfo {
  name: string
  params: Record<string, number | string>
}

const CANONICAL = ['Freespace', 'LOSonly', 'TwoRayGR', 'Null']

const FAMILY_ORDER = [
  'Canonical',
  '3GPP 38.901',
  '3GPP 37.885',
  '3GPP 3D',
  'QuaDRiGa',
  'WINNER',
  'mmMAGIC',
  '5G-ALLSTAR',
  'MIMOSA',
  'BERLIN',
  'DRESDEN',
]

function getFamily(name: string): string {
  if (CANONICAL.includes(name)) return 'Canonical'
  const prefixes = [
    '3GPP_38.901_',
    '3GPP_37.885_',
    '3GPP_3D_',
    'QuaDRiGa_',
    'WINNER_',
    'mmMAGIC_',
    '5G-ALLSTAR_',
    'MIMOSA_',
    'BERLIN_',
    'DRESDEN_',
  ]
  for (const p of prefixes) {
    if (name.startsWith(p)) return p.replace(/_$/, '').replace(/_/g, ' ')
  }
  return 'Other'
}

function getScenarioLabel(name: string, family: string): string {
  if (CANONICAL.includes(name)) return name
  const prefix = family.replace(/ /g, '_') + '_'
  return name.replace(prefix, '').replace(/_/g, ' ')
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
  const clusterVizVisible = useSimulationStore(s => s.clusterVizVisible)
  const setClusterVizVisible = useSimulationStore(s => s.setClusterVizVisible)
  const lspHeatmapVisible = useSimulationStore(s => s.lspHeatmapVisible)
  const setLSPHeatmapVisible = useSimulationStore(s => s.setLSPHeatmapVisible)
  const lspHeatmapParam = useSimulationStore(s => s.lspHeatmapParam)
  const setLSPHeatmapParam = useSimulationStore(s => s.setLSPHeatmapParam)

  const [allPresets, setAllPresets] = useState<PresetInfo[]>([])
  const [presetParams, setPresetParams] = useState<Record<string, number | string>>({})

  const enabled = pathSource === 'stochastic'

  useEffect(() => {
    fetch('/api/channel-presets')
      .then(r => r.json())
      .then((data: PresetInfo[]) => {
        setAllPresets(data)
        const current = data.find(p => p.name === preset)
        if (current) setPresetParams(current.params)
      })
      .catch((err) => { Sentry.captureException(err); useNotificationStore.getState().addNotification('warning', 'Failed to load channel presets') })
  }, [])

  const grouped = useMemo(() => {
    const map = new Map<string, PresetInfo[]>()
    for (const p of allPresets) {
      const fam = getFamily(p.name)
      if (!map.has(fam)) map.set(fam, [])
      map.get(fam)!.push(p)
    }
    return map
  }, [allPresets])

  const families = useMemo(() => {
    return FAMILY_ORDER.filter(f => grouped.has(f))
  }, [grouped])

  const selectedFamily = getFamily(preset)

  const scenarios = useMemo(() => {
    return grouped.get(selectedFamily) ?? []
  }, [grouped, selectedFamily])

  useEffect(() => {
    const p = allPresets.find(p => p.name === preset)
    if (p) setPresetParams(p.params)
  }, [preset, allPresets])

  const selectClass = "w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground"
  const inputClass = selectClass
  const labelClass = "text-xs text-muted-foreground block mt-2 mb-1"

  const getVal = (key: string, fallback: number = 0) =>
    overrides[key] ?? (presetParams[key] as number) ?? fallback

  const setOverride = (key: string, val: number) =>
    setOverrides({ ...overrides, [key]: val })

  const handleFamilyChange = (newFamily: string) => {
    const familyPresets = grouped.get(newFamily) ?? []
    if (familyPresets.length > 0) {
      setPreset(familyPresets[0].name)
      setOverrides({})
    }
  }

  return (
    <div>
      <label className="flex items-center gap-2 text-xs text-foreground">
        <input type="checkbox" checked={enabled}
          onChange={e => setPathSource(e.target.checked ? 'stochastic' : 'synthetic')} />
        Enable stochastic channel
      </label>

      {enabled && (
        <>
          <label className={labelClass}>Standard</label>
          <select className={selectClass} value={selectedFamily}
            onChange={e => handleFamilyChange(e.target.value)}>
            {families.map(f => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>

          <label className={labelClass}>Scenario</label>
          <select className={selectClass} value={preset}
            onChange={e => { setPreset(e.target.value); setOverrides({}) }}>
            {scenarios.map(p => (
              <option key={p.name} value={p.name}>
                {getScenarioLabel(p.name, selectedFamily)}
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
          <div className="flex gap-1.5">
            <input type="number" className={inputClass + ' flex-1'}
              value={seed} onChange={e => setSeed(Number(e.target.value))} />
            <button
              className="px-2 py-1.5 rounded border border-border bg-muted/50 text-foreground hover:bg-muted transition-colors cursor-pointer text-sm"
              title="New channel realization (random seed)"
              onClick={() => setSeed(Math.floor(Math.random() * 2 ** 31))}
            >
              &#x21BB;
            </button>
          </div>

          <button
            className="mt-2 text-xs text-primary hover:underline cursor-pointer"
            onClick={() => setOverrides({})}
          >
            Reset to preset defaults
          </button>

          <hr className="my-3 border-border" />

          <label className="flex items-center gap-2 text-xs text-foreground">
            <input type="checkbox" checked={clusterVizVisible}
              onChange={e => setClusterVizVisible(e.target.checked)} />
            Show cluster rays (FBS/LBS)
          </label>

          <label className="flex items-center gap-2 text-xs text-foreground mt-1">
            <input type="checkbox" checked={lspHeatmapVisible}
              onChange={e => setLSPHeatmapVisible(e.target.checked)} />
            Show LSP heatmap
          </label>

          {lspHeatmapVisible && (
            <>
              <label className={labelClass}>LSP parameter</label>
              <select className={selectClass} value={lspHeatmapParam}
                onChange={e => setLSPHeatmapParam(e.target.value)}>
                {LSP_KEYS.map(k => (
                  <option key={k} value={k}>{getLSPMeta(k).label}</option>
                ))}
              </select>
            </>
          )}
        </>
      )}
    </div>
  )
}
