import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { MarginChart } from './MarginChart'

// ---------------------------------------------------------------------------
// Distance sweep section (client-side 1/r^2 approximation)
// ---------------------------------------------------------------------------

export function DistanceSweepSection() {
  const { stats } = useActiveSimulation()

  const marginDb = stats?.compliance?.margin_db
  const distanceM = stats?.distance_m
  const canSweep = marginDb != null && distanceM != null && distanceM > 0

  // Compute distance sweep data from current compliance margin
  // using far-field 1/r^2 scaling: margin(d) = margin(d0) + 20*log10(d/d0)
  const chartData = (() => {
    if (!canSweep) return []
    const d0 = distanceM!
    const margin0 = marginDb!
    // Range: 0.5m to max(5*d0, 50m), at least 100 points
    const dMax = Math.max(5 * d0, 50)
    const dMin = Math.max(0.5, d0 * 0.1)
    const n = 120
    const data: { x: number; margin: number; compliant: boolean }[] = []
    for (let i = 0; i < n; i++) {
      const d = dMin + (dMax - dMin) * (i / (n - 1))
      const margin = margin0 + 20 * Math.log10(d / d0)
      data.push({ x: parseFloat(d.toFixed(1)), margin: parseFloat(margin.toFixed(2)), compliant: margin >= 0 })
    }
    return data
  })()

  // Find minimum compliant distance (margin = 0 crossing)
  const minCompliantDist = (() => {
    if (!canSweep) return null
    const d0 = distanceM!
    const margin0 = marginDb!
    if (margin0 >= 0) {
      // Already compliant: find where margin = 0
      // margin0 + 20*log10(d/d0) = 0  =>  d = d0 * 10^(-margin0/20)
      const d = d0 * Math.pow(10, -margin0 / 20)
      return d >= 0.1 ? d : null
    }
    // Not compliant: need to move further away
    const d = d0 * Math.pow(10, -margin0 / 20)
    return d
  })()

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Estimate how compliance margin changes with antenna-body distance
        (far-field 1/r&#178; approximation).
      </p>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50">
          Run a compute first
        </span>
      )}
      {canSweep && chartData.length > 0 && (
        <>
          <MarginChart
            data={chartData}
            xLabel="Distance"
            xUnit="m"
            currentX={parseFloat(distanceM!.toFixed(1))}
            maxCompliantX={minCompliantDist != null ? parseFloat(minCompliantDist.toFixed(1)) : null}
          />
          <div className="mt-2 text-xs space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                Current distance: <span className="text-foreground font-medium">{distanceM!.toFixed(1)} m</span>
              </span>
            </div>
            {minCompliantDist != null && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">
                  Min. compliant distance: <span className="text-foreground font-medium">{minCompliantDist.toFixed(1)} m</span>
                </span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
