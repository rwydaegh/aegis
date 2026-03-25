import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { useMIMOStore } from '@/stores/mimo'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { formatSab, formatPower, formatDistance } from '@/lib/format'
import { PHANTOM_META } from '@/components/panels/PhantomPanel'
import Tex from '@/components/ui/Tex'

export default function StatsCard() {
  const { stats } = useActiveSimulation()
  const bodyName = useSceneStore(s => s.bodyName)
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const focusedUser = useMIMOStore(s =>
    s.focusedUserId ? s.users.get(s.focusedUserId) ?? null : null
  )
  const phantomName = mimoEnabled && focusedUser ? focusedUser.phantomName : bodyName
  const isComputing = useUIStore(s => s.isComputing)
  const meta = PHANTOM_META[phantomName.toLowerCase()]
  const massKg = meta?.mass_kg

  const sarValue = (stats && massKg) ? (stats.p_abs_mw / 1000) / massKg : null
  const formatSar = (sar: number) => {
    if (sar >= 0.01) return `${sar.toFixed(3)} W/kg`
    if (sar >= 1e-5) return `${(sar * 1e3).toFixed(3)} mW/kg`
    return `${sar.toExponential(2)} W/kg`
  }

  const rows: Array<{ key: string; label: React.ReactNode; value: string; highlight?: 'pass' | 'fail' }> = [
    {
      key: 'sar_wb',
      label: <Tex math={'\\text{SAR}_\\text{wb}'} />,
      value: sarValue != null ? formatSar(sarValue) : '--',
    },
    {
      key: 'p_abs',
      label: <Tex math={'P_\\text{abs}'} />,
      value: stats ? formatPower(stats.p_abs_mw) : '--',
    },
    {
      key: 'peak_sab',
      label: <Tex math={'\\text{Peak}\\;S_\\text{ab}'} />,
      value: stats ? formatSab(stats.peak_sab) : '--',
    },
    {
      key: 'distance',
      label: 'Distance',
      value: stats ? formatDistance(stats.distance_m) : '--',
    },
    {
      key: 'illuminated',
      label: 'Illuminated',
      value: stats ? `${stats.n_illuminated} / ${stats.n_triangles}` : '--',
    },
    {
      key: 'compliance',
      label: 'Compliance',
      value: stats ? (stats.compliant ? 'PASS' : 'FAIL') : '--',
      highlight: stats ? (stats.compliant ? 'pass' : 'fail') : undefined,
    },
  ]

  return (
    <div className={`bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 min-w-[180px] ${isComputing ? 'shimmer-panel' : ''}`}>
      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
        Dosimetry
      </p>
      <dl className="space-y-1">
        {rows.map(({ key, label, value, highlight }) => (
          <div key={key} className="flex items-baseline justify-between gap-3">
            <dt className="text-xs text-muted-foreground shrink-0">{label}</dt>
            <dd
              className={
                'text-xs font-mono tabular-nums font-medium ' +
                (highlight === 'pass'
                  ? 'text-success'
                  : highlight === 'fail'
                    ? 'text-destructive'
                    : 'text-foreground')
              }
            >
              {value}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
