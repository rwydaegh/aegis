import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import type { DosimetryMode } from '@/stores/simulation'
import type { DisplayMode } from '@/stores/ui'

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
  const tissue = useSimulationStore((s) => s.tissue)
  const setTissue = useSimulationStore((s) => s.setTissue)
  const nPaths = useSimulationStore((s) => s.nPaths)
  const setNPaths = useSimulationStore((s) => s.setNPaths)
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const setFreqGhz = useSimulationStore((s) => s.setFreqGhz)

  const displayMode = useUIStore((s) => s.displayMode)
  const setDisplayMode = useUIStore((s) => s.setDisplayMode)
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

      <label className={labelClass}>TX power (dBm)</label>
      <input
        type="number"
        className={inputClass}
        value={powerDbm}
        onChange={(e) => setPowerDbm(Number(e.target.value))}
      />

      <label className={labelClass}>Tissue</label>
      <select
        className={selectClass}
        value={tissue}
        onChange={(e) => setTissue(e.target.value)}
      >
        {caps.tissues.map((t) => (
          <option key={t} value={t}>
            {t.replace(/_/g, ' ')}
          </option>
        ))}
      </select>

      <label className={labelClass}>Paths</label>
      <select
        className={selectClass}
        value={nPaths}
        onChange={(e) => setNPaths(Number(e.target.value))}
      >
        {config.dosimetry.path_options.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>

      <label className={labelClass}>Frequency (GHz)</label>
      <div className="flex gap-1 items-center">
        <input
          type="number"
          className={inputClass + ' !w-[70px]'}
          value={freqGhz}
          onChange={(e) => setFreqGhz(parseFloat(e.target.value) || 28)}
          min={6.1}
          max={300}
          step={0.1}
        />
        {[28, 39, 60].map((f) => (
          <button
            key={f}
            onClick={() => setFreqGhz(f)}
            className={`text-[11px] px-2 py-1 rounded border transition-colors cursor-pointer ${
              freqGhz === f
                ? 'border-primary/40 bg-primary/15 text-primary'
                : 'border-border bg-muted/50 text-foreground hover:bg-muted'
            }`}
          >
            {f}
          </button>
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

      <label className={labelClass}>Display</label>
      <select
        className={selectClass}
        value={displayMode}
        onChange={(e) => setDisplayMode(e.target.value as DisplayMode)}
      >
        <option value="raw_sab">Raw S_ab</option>
        <option value="avg_sab">Averaged S_ab (4 cm&#178;)</option>
        <option value="sinc">S_inc (incident)</option>
        <option value="ratio_sab">Compliance ratio (S_ab)</option>
        <option value="ratio_sinc">Compliance ratio (S_inc)</option>
      </select>
    </div>
  )
}
