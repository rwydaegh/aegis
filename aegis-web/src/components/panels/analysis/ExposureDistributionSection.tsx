import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { formatSabNumber } from './utils'

// ---------------------------------------------------------------------------
// Exposure distribution section
// ---------------------------------------------------------------------------

export function ExposureDistributionSection() {
  const { stats, sabArray } = useActiveSimulation()
  const dist = stats?.distribution

  if (!dist || !sabArray || sabArray.length === 0) {
    return (
      <span className="text-[10px] text-muted-foreground/50">
        Run a compute first
      </span>
    )
  }

  const illumPct = (dist.illuminated_fraction * 100).toFixed(1)

  return (
    <div className="space-y-2">
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Distribution of absorbed power density across the body mesh.
      </p>

      {/* Illumination coverage */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">Illuminated</span>
          <span className="font-mono text-foreground">
            {illumPct}%
            <span className="text-muted-foreground ml-1">
              ({stats.n_illuminated.toLocaleString()} / {stats.n_triangles.toLocaleString()})
            </span>
          </span>
        </div>
        <div className="h-1.5 bg-muted/50 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary/70 rounded-full transition-all"
            style={{ width: `${Math.min(dist.illuminated_fraction * 100, 100)}%` }}
          />
        </div>
      </div>

      {dist.illuminated_area_cm2 != null && (
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">Illuminated area</span>
          <span className="font-mono text-foreground">{dist.illuminated_area_cm2.toFixed(1)} cm&sup2;</span>
        </div>
      )}

      {/* Distribution table */}
      <div className="border border-border/40 rounded overflow-hidden">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="bg-muted/30 text-muted-foreground">
              <th className="text-left py-1 px-2 font-medium">Statistic</th>
              <th className="text-right py-1 px-2 font-medium">W/m&sup2;</th>
            </tr>
          </thead>
          <tbody className="font-mono">
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Peak</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSabNumber(stats.peak_sab)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">P99</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSabNumber(dist.p99)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">P95</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSabNumber(dist.p95)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Mean (all)</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSabNumber(dist.mean)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Mean (illuminated)</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSabNumber(dist.illuminated_mean)}</td>
            </tr>
            <tr className="border-t border-border/20">
              <td className="py-0.5 px-2 text-muted-foreground">Median (illuminated)</td>
              <td className="py-0.5 px-2 text-right text-foreground">{formatSabNumber(dist.illuminated_p50)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
