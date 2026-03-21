import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { formatSab, formatPower, formatDistance } from '@/lib/format'

function StatsCard() {
  const { stats } = useSimulationStore()

  const rows: Array<{ label: string; value: string; highlight?: 'pass' | 'fail' }> = [
    {
      label: 'P_abs',
      value: stats ? formatPower(stats.p_abs_mw) : '--',
    },
    {
      label: 'Peak S_ab',
      value: stats ? formatSab(stats.peak_sab) : '--',
    },
    {
      label: 'S_inc',
      value: stats ? formatSab(stats.S_inc) : '--',
    },
    {
      label: 'Distance',
      value: stats ? formatDistance(stats.distance_m) : '--',
    },
    {
      label: 'Illuminated',
      value: stats ? `${stats.n_illuminated} / ${stats.n_triangles}` : '--',
    },
    {
      label: 'Compliance',
      value: stats ? (stats.compliant ? 'PASS' : 'FAIL') : '--',
      highlight: stats ? (stats.compliant ? 'pass' : 'fail') : undefined,
    },
  ]

  return (
    <div className="bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 min-w-[180px]">
      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">
        Dosimetry
      </p>
      <dl className="space-y-1">
        {rows.map(({ label, value, highlight }) => (
          <div key={label} className="flex items-baseline justify-between gap-3">
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

function StatusBar() {
  const { isComputing, computeElapsed, statusMessage } = useUIStore()

  if (!isComputing && !statusMessage) return null

  return (
    <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-2
      bg-card/90 backdrop-blur-md rounded-full border border-border px-4 py-2">
      {isComputing && (
        <>
          <div className="w-3 h-3 border-2 border-muted border-t-primary rounded-full animate-spin" />
          <span className="text-xs text-muted-foreground">
            Computing{computeElapsed > 0 ? ` (${(computeElapsed / 1000).toFixed(1)}s)` : '...'}
          </span>
        </>
      )}
      {!isComputing && statusMessage && (
        <span className="text-xs text-muted-foreground">{statusMessage}</span>
      )}
    </div>
  )
}

export default function HudOverlay() {
  return (
    <div className="absolute inset-0 pointer-events-none z-10">
      {/* Stats card - top right */}
      <div className="absolute top-3 right-3 pointer-events-auto">
        <StatsCard />
      </div>

      {/* Color legend - right edge, vertically centered (placeholder for Task 14) */}
      <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-auto">
        {/* Color legend will be implemented in Task 14 */}
      </div>

      {/* Status bar - bottom center */}
      <div className="pointer-events-auto">
        <StatusBar />
      </div>
    </div>
  )
}
