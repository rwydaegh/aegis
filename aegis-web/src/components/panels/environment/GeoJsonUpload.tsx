import { useRef, useState } from 'react'
import { useEnvironmentStore } from '@/stores/environment'
import { Loader2 } from 'lucide-react'
import { labelClass } from './constants'

export function GeoJsonUpload() {
  const loading = useEnvironmentStore((s) => s.loading)
  const geocoding = useEnvironmentStore((s) => s.geocoding)
  const fetchGeoJSON = useEnvironmentStore((s) => s.fetchGeoJSON)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [geojsonFileName, setGeoJsonFileName] = useState<string | null>(null)

  const busy = loading || geocoding

  return (
    <div className="space-y-2 pt-1 border-t border-border">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
        GeoJSON
      </p>
      <div className="space-y-1">
        <label className={labelClass}>Upload a .geojson or .json file</label>
        <input
          ref={fileInputRef}
          type="file"
          accept=".geojson,.json"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (!file) return
            setGeoJsonFileName(file.name)
            const reader = new FileReader()
            reader.onload = (evt) => {
              const text = evt.target?.result as string
              if (text) void fetchGeoJSON(text)
            }
            reader.readAsText(file)
            // reset so the same file can be re-selected
            e.target.value = ''
          }}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={busy}
          className="w-full px-3 py-1.5 rounded text-xs font-medium bg-muted text-muted-foreground hover:text-foreground disabled:opacity-50 flex items-center justify-center gap-1.5"
        >
          {loading && geojsonFileName ? (
            <Loader2 className="size-3 animate-spin" />
          ) : null}
          Choose file
        </button>
        {geojsonFileName && (
          <p className="text-xs text-muted-foreground truncate">
            {geojsonFileName}
          </p>
        )}
      </div>
    </div>
  )
}
