import { useSimulationStore } from '@/stores/simulation'
import { useSceneStore } from '@/stores/scene'

export default function ParametersPanel() {
  const level = useSimulationStore((s) => s.level)
  const setLevel = useSimulationStore((s) => s.setLevel)
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
      <label className={labelClass}>Fidelity level</label>
      <select
        className={selectClass}
        value={level}
        onChange={(e) => setLevel(Number(e.target.value))}
      >
        {config.dosimetry.fidelity_levels.map((l) => (
          <option key={l.value} value={l.value}>
            {l.label}
          </option>
        ))}
      </select>

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
