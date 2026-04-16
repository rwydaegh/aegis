import { useEnvironmentStore } from '@/stores/environment'
import { Loader2, Search } from 'lucide-react'
import { inputClass, labelClass } from './constants'

export function LocationSearch() {
  const location = useEnvironmentStore((s) => s.location)
  const locationQuery = useEnvironmentStore((s) => s.locationQuery)
  const locationFormatted = useEnvironmentStore((s) => s.locationFormatted)
  const loading = useEnvironmentStore((s) => s.loading)
  const geocoding = useEnvironmentStore((s) => s.geocoding)
  const setLocationQuery = useEnvironmentStore((s) => s.setLocationQuery)
  const geocodeAndFetch = useEnvironmentStore((s) => s.geocodeAndFetch)

  const busy = loading || geocoding

  return (
    <div>
      <label className={labelClass}>Location</label>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          void geocodeAndFetch()
        }}
        className="flex gap-1.5"
      >
        <input
          type="text"
          placeholder="e.g. Ghent, Belgium"
          value={locationQuery}
          onChange={(e) => setLocationQuery(e.target.value)}
          className={inputClass}
        />
        <button
          type="submit"
          disabled={busy || !locationQuery.trim()}
          className="px-2.5 py-1.5 rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center shrink-0"
        >
          {geocoding ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Search className="size-3.5" />
          )}
        </button>
      </form>
      {locationFormatted && location && (
        <p className="text-xs text-muted-foreground mt-1">
          {locationFormatted} ({location.lat.toFixed(4)}, {location.lon.toFixed(4)})
        </p>
      )}
    </div>
  )
}
