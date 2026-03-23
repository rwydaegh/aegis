import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'
import type { DosimetryMode } from '@/stores/simulation'

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
    </div>
  )
}
