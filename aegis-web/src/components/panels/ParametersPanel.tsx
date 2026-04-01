import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import { useBaseStationsStore } from '@/stores/basestations'
import type { DosimetryMode, ExposureMode } from '@/stores/simulation'
import QuantitiesPanel from './QuantitiesPanel'
import Tex from '@/components/ui/Tex'

const MODES: { value: DosimetryMode; label: string }[] = [
  { value: 'bound', label: 'Bound' },
  { value: 'aggregate', label: 'Aggregate' },
  { value: 'spatial', label: 'Spatial' },
]

function CorrectionToggle({
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

export default function ParametersPanel() {
  const antennaPos = useSimulationStore((s) => s.antennaPos)
  const setAntennaPos = useSimulationStore((s) => s.setAntennaPos)
  const clearResults = useSimulationStore((s) => s.clearResults)
  const mode = useSimulationStore((s) => s.mode)
  const setMode = useSimulationStore((s) => s.setMode)
  const fresnel = useSimulationStore((s) => s.fresnel)
  const setFresnel = useSimulationStore((s) => s.setFresnel)
  const polarisation = useSimulationStore((s) => s.polarisation)
  const setPolarisation = useSimulationStore((s) => s.setPolarisation)
  const curvature = useSimulationStore((s) => s.curvature)
  const setCurvature = useSimulationStore((s) => s.setCurvature)
  const diffraction = useSimulationStore((s) => s.diffraction)
  const setDiffraction = useSimulationStore((s) => s.setDiffraction)
  const powerDbm = useSimulationStore((s) => s.powerDbm)
  const setPowerDbm = useSimulationStore((s) => s.setPowerDbm)
  const skinModel = useSimulationStore((s) => s.skinModel)
  const setSkinModel = useSimulationStore((s) => s.setSkinModel)
  const stats = useSimulationStore((s) => s.stats)
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const setFreqGhz = useSimulationStore((s) => s.setFreqGhz)
  const exposureMode = useSimulationStore((s) => s.exposureMode)
  const setExposureMode = useSimulationStore((s) => s.setExposureMode)

  const bsCount = useBaseStationsStore((s) => s.basestations.length)

  const scenario = useUIStore((s) => s.exposureScenario)
  const setScenario = useUIStore((s) => s.setExposureScenario)

  const config = useSceneStore((s) => s.viewerConfig)
  const caps = useSceneStore((s) => s.capabilities)

  if (!config || !caps) return null

  const selectClass =
    'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring'
  const inputClass = selectClass
  const labelClass = 'text-xs text-muted-foreground block mt-3 mb-1'

  return (
    <div>
      {antennaPos && (
        <button
          className="w-full mb-3 px-3 py-1.5 text-xs rounded border border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20 transition-colors cursor-pointer"
          onClick={() => {
            setAntennaPos(null)
            clearResults()
            const mimo = useMIMOStore.getState()
            if (mimo.enabled) {
              mimo.clearAllResults()
              mimo.setPrecoderWeights(null)
              useMIMOStore.setState({ arrayConfig: null })
            }
          }}
        >
          Remove antenna
        </button>
      )}
      <label className={labelClass}>Computation mode</label>
      <select
        className={selectClass}
        value={mode}
        onChange={(e) => setMode(e.target.value as DosimetryMode)}
      >
        {MODES.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>

      {mode === 'spatial' && (
        <>
          <label className={labelClass}>Physics corrections</label>
          <div className="flex flex-col gap-1.5 pl-0.5">
            <CorrectionToggle
              label="Fresnel"
              checked={fresnel}
              onChange={setFresnel}
            />
            <CorrectionToggle
              label="Polarisation"
              checked={polarisation}
              onChange={setPolarisation}
              disabled={!fresnel}
              title={!fresnel ? 'Requires Fresnel' : undefined}
            />
            <CorrectionToggle
              label="Curvature"
              checked={curvature}
              onChange={setCurvature}
              disabled={diffraction}
              title={diffraction ? 'Required by diffraction' : undefined}
            />
            <CorrectionToggle
              label="Diffraction"
              checked={diffraction}
              onChange={setDiffraction}
            />
          </div>
        </>
      )}

      <label className={labelClass}><Tex math={'P_\\text{TX}'} /></label>
      <div className="flex gap-2 items-center">
        <div className="flex-1">
          <input
            type="number"
            className={inputClass + ' !w-full'}
            value={powerDbm}
            onChange={(e) => setPowerDbm(Number(e.target.value))}
            step={1}
          />
          <span className="text-[10px] text-muted-foreground mt-0.5 block">dBm</span>
        </div>
        <span className="text-muted-foreground text-xs pb-3">=</span>
        <div className="flex-1">
          <input
            type="number"
            className={inputClass + ' !w-full'}
            value={Number((10 ** ((powerDbm - 30) / 10)).toPrecision(4))}
            onChange={(e) => {
              const w = Number(e.target.value)
              if (w > 0) setPowerDbm(Math.round((10 * Math.log10(w) + 30) * 100) / 100)
            }}
            step={0.1}
            min={0}
          />
          <span className="text-[10px] text-muted-foreground mt-0.5 block">W</span>
        </div>
      </div>

      {bsCount > 0 && (
        <>
          <label className={labelClass}>Exposure mode</label>
          <div className="flex gap-0">
            {([
              { value: 'theoretical' as ExposureMode, label: 'Theoretical', title: 'Full EIRP, no reduction' },
              { value: 'actual_max' as ExposureMode, label: 'Actual max', title: 'TDD duty cycle + power reduction factor' },
              { value: 'typical' as ExposureMode, label: 'Typical', title: 'TDD + PRF + traffic load (~50%)' },
            ]).map(({ value, label, title }, i) => (
              <button
                key={value}
                title={title}
                className={`text-xs px-3 py-1.5 border transition-colors cursor-pointer ${
                  i === 0 ? 'rounded-l' : i === 2 ? 'rounded-r border-l-0' : 'border-l-0'
                } ${
                  exposureMode === value
                    ? 'border-primary/40 bg-primary/15 text-primary'
                    : 'border-border bg-muted/50 text-foreground hover:bg-muted'
                }`}
                onClick={() => setExposureMode(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </>
      )}

      <label className={labelClass}>Skin model</label>
      <select
        className={selectClass}
        value={skinModel}
        onChange={(e) => setSkinModel(e.target.value)}
      >
        {caps.skin_models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.label}
          </option>
        ))}
      </select>
      {stats?.tissue_eps_r != null && (
        <div className="flex gap-3 mt-1 text-[10px] text-muted-foreground">
          <span><Tex math={`\\varepsilon_r = ${stats.tissue_eps_r.toFixed(1)}`} /></span>
          <span><Tex math={`\\sigma = ${stats.tissue_sigma.toFixed(1)}\\;\\text{S/m}`} /></span>
        </div>
      )}

      <label className={labelClass}><Tex math={'f\\;(\\text{GHz})'} /></label>
      <div className="flex gap-1.5 items-center mb-2">
        <input
          type="number"
          className={inputClass + ' !w-[70px]'}
          value={freqGhz}
          onChange={(e) => {
            const v = parseFloat(e.target.value)
            if (!Number.isFinite(v)) return
            setFreqGhz(Math.max(0.3, Math.min(300, v)))
          }}
          min={0.3}
          max={300}
          step={1}
        />
        <span className="text-[10px] text-muted-foreground">GHz</span>
      </div>
      <div className="flex flex-col gap-1.5">
        {([
          { label: 'Sub-6', freqs: [0.9, 1.8, 2.1, 2.4, 3.5, 5, 5.8] },
          { label: 'FR3 (6G)', freqs: [7, 10, 15] },
          { label: 'FR2 (5G)', freqs: [26, 28, 39, 47] },
          { label: '60+', freqs: [60, 77, 100] },
        ] as const).map((group) => (
          <div key={group.label} className="flex items-center gap-1">
            <span className="text-[9px] text-muted-foreground w-[46px] shrink-0 text-right pr-1">
              {group.label}
            </span>
            <div className="flex flex-wrap gap-0.5">
              {group.freqs.map((f) => (
                <button
                  key={f}
                  onClick={() => setFreqGhz(f)}
                  className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                    freqGhz === f
                      ? 'border-primary/40 bg-primary/15 text-primary'
                      : 'border-border bg-muted/50 text-foreground hover:bg-muted'
                  }`}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      <label className={labelClass}>Exposure scenario</label>
      <div className="flex gap-0">
        <button
          className={`text-xs px-3 py-1.5 rounded-l border transition-colors cursor-pointer ${
            scenario === 'general_public'
              ? 'border-primary/40 bg-primary/15 text-primary'
              : 'border-border bg-muted/50 text-foreground hover:bg-muted'
          }`}
          onClick={() => setScenario('general_public')}
        >
          General Public
        </button>
        <button
          className={`text-xs px-3 py-1.5 rounded-r border border-l-0 transition-colors cursor-pointer ${
            scenario === 'occupational'
              ? 'border-primary/40 bg-primary/15 text-primary'
              : 'border-border bg-muted/50 text-foreground hover:bg-muted'
          }`}
          onClick={() => setScenario('occupational')}
        >
          Occupational
        </button>
      </div>

      <label className={labelClass}>Quantities</label>
      <QuantitiesPanel />
    </div>
  )
}
