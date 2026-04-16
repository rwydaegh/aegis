import * as Sentry from '@sentry/react'
import { useEnvironmentStore } from '@/stores/environment'

export function ExportButton() {
  const loading = useEnvironmentStore((s) => s.loading)
  const geocoding = useEnvironmentStore((s) => s.geocoding)
  const exportForRT = useEnvironmentStore((s) => s.exportForRT)

  const busy = loading || geocoding

  return (
    <div className="flex gap-2 pt-1">
      <button
        onClick={() => void exportForRT('differt').catch(err => Sentry.captureException(err))}
        disabled={busy}
        className="px-3 py-1.5 rounded text-xs font-medium bg-muted text-muted-foreground hover:text-foreground disabled:opacity-50"
      >
        Export
      </button>
    </div>
  )
}
