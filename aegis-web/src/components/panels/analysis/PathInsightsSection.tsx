import { useState, useRef, useEffect } from 'react'
import * as Sentry from '@sentry/react'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { useSceneStore } from '@/stores/scene'
import { useNotificationStore } from '@/stores/notifications'
import { fetchPathContributions } from '@/api/client'
import type { PathContributionsResult } from '@/api/client'
import { formatSabNumber } from './utils'

// ---------------------------------------------------------------------------
// Path insights section
//
// After a ray-traced compute, reveal which propagation paths dominate the
// peak absorbed power density. Backed by aegis.analysis.path_contributions
// and path_importance. The physics: for the geometric+Fresnel kernel,
// contribution c_{m,n} = T_avg(mu_{m,n}) * ReLU(mu_{m,n}) * power_n, and
// S_ab(m) = sum_n c_{m,n}.
// ---------------------------------------------------------------------------

const TOP_K = 5

function formatPower(v: number | null): string {
  if (v == null || !isFinite(v)) return '—'
  return formatSabNumber(v)
}

function pathLabel(is_los: boolean, index: number): string {
  return `${is_los ? 'LOS' : 'NLOS'} #${index}`
}

export function PathInsightsSection() {
  const { stats, sabArray } = useActiveSimulation()
  const rtPaths = useSceneStore((s) => s.rtPaths)

  const [result, setResult] = useState<PathContributionsResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fetchTokenRef = useRef(0)

  // Fire a fetch whenever the dosimetry stats or RT paths change.
  // `stats` identity changes with every compute; `rtPaths` becomes non-null
  // only after an RT compute, so non-RT computes skip this fetch.
  useEffect(() => {
    if (!stats || !rtPaths || rtPaths.length === 0) {
      setResult(null)
      setError(null)
      return
    }
    const token = ++fetchTokenRef.current
    setLoading(true)
    setError(null)
    fetchPathContributions({ top_k: TOP_K })
      .then((data) => {
        if (fetchTokenRef.current !== token) return
        setResult(data)
      })
      .catch((err) => {
        if (fetchTokenRef.current !== token) return
        setResult(null)
        setError(err instanceof Error ? err.message : 'fetch failed')
        Sentry.captureException(err)
        useNotificationStore
          .getState()
          .addNotification('warning', 'Path insights unavailable for this compute')
      })
      .finally(() => {
        if (fetchTokenRef.current === token) setLoading(false)
      })
  }, [stats, rtPaths])

  if (!rtPaths || rtPaths.length === 0 || !sabArray || sabArray.length === 0) {
    return (
      <span className="text-[10px] text-muted-foreground/50">
        Run a ray-traced compute to see which paths drive the peak exposure.
      </span>
    )
  }

  if (loading && !result) {
    return <span className="text-[10px] text-muted-foreground/60">Analyzing paths…</span>
  }

  if (error) {
    return (
      <span className="text-[10px] text-destructive">
        Could not load path contributions.
      </span>
    )
  }

  if (!result || result.paths.length === 0) {
    return (
      <span className="text-[10px] text-muted-foreground/60">
        No path contributions available.
      </span>
    )
  }

  const topShare = result.paths[result.paths.length - 1]?.cumulative ?? null
  const importanceTotal = result.importance.p_abs_total
  const shownImportanceSum = result.importance.top.reduce(
    (acc, r) => acc + (r.fraction ?? 0),
    0,
  )

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-muted-foreground/60">
        Ranks paths by their contribution to peak S<sub>ab</sub> (top) and to whole-body
        absorbed power (bottom). Built from {result.n_paths} ray-traced paths ({result.n_los} LOS
        / {result.n_nlos} NLOS).
      </p>

      {/* Top paths driving the peak triangle */}
      <div className="space-y-1">
        <div className="flex items-baseline justify-between text-[11px]">
          <span className="text-muted-foreground">
            Top {result.paths.length} paths at peak triangle
          </span>
          {topShare != null && (
            <span className="font-mono text-foreground">
              {(topShare * 100).toFixed(0)}% of peak
            </span>
          )}
        </div>
        <div className="border border-border/40 rounded overflow-hidden">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="bg-muted/30 text-muted-foreground">
                <th className="text-left py-1 px-2 font-medium">Path</th>
                <th className="text-right py-1 px-2 font-medium">W/m&sup2;</th>
                <th className="text-right py-1 px-2 font-medium">% of peak</th>
                <th className="text-left py-1 px-2 font-medium w-[72px]">Share</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {result.paths.map((p) => {
                const pct = p.fraction != null ? (p.fraction * 100).toFixed(1) : '—'
                const width = p.fraction != null ? Math.min(Math.max(p.fraction * 100, 0), 100) : 0
                return (
                  <tr key={`peak-${p.index}`} className="border-t border-border/20">
                    <td className="py-0.5 px-2 text-foreground">
                      {pathLabel(p.is_los, p.index)}
                    </td>
                    <td className="py-0.5 px-2 text-right text-foreground">
                      {formatPower(p.contribution_w_m2)}
                    </td>
                    <td className="py-0.5 px-2 text-right text-foreground">{pct}%</td>
                    <td className="py-0.5 px-2">
                      <div className="h-1.5 bg-muted/40 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${p.is_los ? 'bg-primary/70' : 'bg-orange-400/70'}`}
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Whole-body importance */}
      <div className="space-y-1">
        <div className="flex items-baseline justify-between text-[11px]">
          <span className="text-muted-foreground">
            Top {result.importance.top.length} paths by whole-body P<sub>abs</sub>
          </span>
          {importanceTotal != null && (
            <span className="font-mono text-foreground">
              {(shownImportanceSum * 100).toFixed(0)}% of P<sub>abs</sub>
            </span>
          )}
        </div>
        <div className="border border-border/40 rounded overflow-hidden">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="bg-muted/30 text-muted-foreground">
                <th className="text-left py-1 px-2 font-medium">Path</th>
                <th className="text-right py-1 px-2 font-medium">W</th>
                <th className="text-right py-1 px-2 font-medium">% of total</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {result.importance.top.map((p) => {
                const pct = p.fraction != null ? (p.fraction * 100).toFixed(1) : '—'
                return (
                  <tr key={`imp-${p.index}`} className="border-t border-border/20">
                    <td className="py-0.5 px-2 text-foreground">
                      {pathLabel(p.is_los, p.index)}
                    </td>
                    <td className="py-0.5 px-2 text-right text-foreground">
                      {formatPower(p.importance_w)}
                    </td>
                    <td className="py-0.5 px-2 text-right text-foreground">{pct}%</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
