import { useEffect, useRef, useState } from 'react'
import { searchPatterns } from '@/api/patterns'
import type { PatternSearchResult } from '@/api/patterns'
import { useSimulationStore } from '@/stores/simulation'

type SourceFilter = 'all' | 'local' | 'cloudrf'

export default function PatternBrowserPanel() {
  const [query, setQuery] = useState('')
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>('all')
  const [results, setResults] = useState<PatternSearchResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const selectedPattern = useSimulationStore(s => s.selectedPattern)
  const setSelectedPattern = useSimulationStore(s => s.setSelectedPattern)

  const labelClass = 'text-xs text-muted-foreground block mt-3 mb-1'
  const inputClass =
    'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring'

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setIsLoading(true)
      setError(null)
      try {
        const params: Parameters<typeof searchPatterns>[0] = { limit: 50 }
        if (query.trim()) params.q = query.trim()
        if (sourceFilter !== 'all') params.source = sourceFilter
        const data = await searchPatterns(params)
        setResults(data.results)
      } catch (err) {
        setError((err as Error).message)
        setResults([])
      } finally {
        setIsLoading(false)
      }
    }, 300)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [query, sourceFilter])

  const handleSelect = (r: PatternSearchResult) => {
    setSelectedPattern({
      source: r.source,
      id: r.id,
      manufacturer: r.manufacturer,
      model: r.model,
      gain_dbi: r.gain_dbi,
    })
  }

  const handleClear = () => setSelectedPattern(null)

  const sourceButtons: { label: string; value: SourceFilter }[] = [
    { label: 'All', value: 'all' },
    { label: 'Local', value: 'local' },
    { label: 'CloudRF', value: 'cloudrf' },
  ]

  return (
    <div>
      {selectedPattern && (
        <div className="mb-3 p-2 rounded border border-primary/40 bg-primary/10 text-xs">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="font-medium text-foreground truncate">{selectedPattern.manufacturer}</p>
              <p className="text-muted-foreground truncate">{selectedPattern.model}</p>
              <p className="text-muted-foreground">{selectedPattern.gain_dbi} dBi &middot; {selectedPattern.source}</p>
            </div>
            <button
              className="shrink-0 px-2 py-0.5 text-xs rounded border border-border bg-muted/50 text-foreground hover:bg-muted transition-colors cursor-pointer"
              onClick={handleClear}
            >
              Clear
            </button>
          </div>
        </div>
      )}

      <label className={labelClass}>Search</label>
      <input
        type="text"
        className={inputClass}
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="e.g. Kathrein, 742 215..."
      />

      <label className={labelClass}>Source</label>
      <div className="flex gap-1">
        {sourceButtons.map(btn => (
          <button
            key={btn.value}
            className={`flex-1 px-2 py-1 text-xs rounded border transition-colors cursor-pointer ${
              sourceFilter === btn.value
                ? 'border-primary/60 bg-primary/20 text-primary'
                : 'border-border bg-muted/40 text-muted-foreground hover:bg-muted'
            }`}
            onClick={() => setSourceFilter(btn.value)}
          >
            {btn.label}
          </button>
        ))}
      </div>

      <div className="mt-3">
        {isLoading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground py-2">
            <span className="w-3 h-3 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
            Searching...
          </div>
        ) : error ? (
          <p className="text-xs text-destructive py-2">{error}</p>
        ) : results.length === 0 ? (
          <p className="text-xs text-muted-foreground py-2">
            {query.trim() ? 'No patterns found.' : 'Type to search patterns.'}
          </p>
        ) : (
          <>
            <p className="text-xs text-muted-foreground mb-1">{results.length} result{results.length !== 1 ? 's' : ''}</p>
            <div className="overflow-y-auto max-h-[300px] flex flex-col gap-0.5 pr-0.5">
              {results.map(r => {
                const isSelected = selectedPattern?.source === r.source && selectedPattern?.id === r.id
                return (
                  <button
                    key={`${r.source}:${r.id}`}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs border transition-colors cursor-pointer ${
                      isSelected
                        ? 'border-primary/60 bg-primary/20 text-primary'
                        : 'border-transparent bg-muted/30 text-foreground hover:bg-muted/60'
                    }`}
                    onClick={() => handleSelect(r)}
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="font-medium truncate">{r.manufacturer}</span>
                      <span className="shrink-0 text-muted-foreground">{r.gain_dbi} dBi</span>
                    </div>
                    <div className="flex items-baseline justify-between gap-2 mt-0.5">
                      <span className="text-muted-foreground truncate">{r.model}</span>
                      <span className="shrink-0 text-muted-foreground">{r.frequency_mhz} MHz</span>
                    </div>
                  </button>
                )
              })}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
