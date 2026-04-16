import { useCoverageStore } from '@/stores/coverage'
import { Loader2 } from 'lucide-react'

export function CoverageStatus() {
  const coverageLoading = useCoverageStore((s) => s.loading)
  const coverageLoaded = useCoverageStore((s) => s.loaded)
  const coverageError = useCoverageStore((s) => s.error)
  const coverageSiteCount = useCoverageStore((s) => s.siteCount)
  const coverageRegionCount = useCoverageStore((s) => s.regions.length)

  return (
    <div className="space-y-2 pt-1 border-t border-border">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        Coverage
      </p>
      {coverageLoading && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" />
          Loading coverage data...
        </div>
      )}
      {coverageError && (
        <p className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1.5">
          {coverageError}
        </p>
      )}
      {coverageLoaded && !coverageError && (
        <p className="text-xs text-muted-foreground">
          {coverageSiteCount.toLocaleString()} sites loaded across {coverageRegionCount} regions.
        </p>
      )}
    </div>
  )
}
