import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import type { BaseStationData } from '@/api/basestations'
import { SOURCE_URLS, FIELD_LABELS } from '@/utils/fidelityTier'

/** License strings per source_tag, hardcoded from regulator metadata. */
const SOURCE_LICENSES: Record<string, string> = {
  'gov:brussels': 'BIPT Open Data',
  'gov:flanders': 'BIPT Open Data',
  'gov:anfr': 'Etalab Open License v2.0',
  'gov:antenneregister': 'Dutch Open Data',
  'gov:bnetza': 'BNetzA (terms vary)',
  'gov:mastedatabasen': 'Danish Open Data',
  'gov:rtr': 'RTR Austria (open access)',
  'gov:acma': 'CC-BY 4.0',
  'gov:uke': 'Polish Open Data',
  'gov:vctel': 'Restricted (non-commercial)',
  'gov:bakom': 'Swiss Open Data',
  'gov:ised': 'Crown Copyright (permissive)',
  'gov:ofcom_wtr': 'OGL v3.0',
}

/** Region display names derived from source tags. */
const SOURCE_REGION_NAMES: Record<string, string> = {
  'gov:brussels': 'Brussels, Belgium',
  'gov:flanders': 'Flanders, Belgium',
  'gov:anfr': 'France',
  'gov:antenneregister': 'Netherlands',
  'gov:bnetza': 'Germany',
  'gov:mastedatabasen': 'Denmark',
  'gov:rtr': 'Austria',
  'gov:acma': 'Australia',
  'gov:uke': 'Poland',
  'gov:vctel': 'Spain',
  'gov:bakom': 'Switzerland',
  'gov:ised': 'Canada',
  'gov:ofcom_wtr': 'United Kingdom',
}

/** Provenance field keys to display in the completion bars. */
const PROVENANCE_FIELDS = [
  'Power',
  'Frequency',
  'Azimuth',
  'CenterHeight',
  'Gain',
  'Electrical_Tilt',
  'Mechanical_Tilt',
  'Horizontal_Beamwidth',
  'Vertical_Beamwidth',
] as const

/** Map from provenance_sources keys (API field names) to canonical provenance field names. */
const API_TO_PROV: Record<string, string> = {
  eirp_dbm: 'Power',
  azimuth_deg: 'Azimuth',
  height_m: 'CenterHeight',
  freq_mhz: 'Frequency',
  gain_dbi: 'Gain',
  electrical_tilt_deg: 'Electrical_Tilt',
  mechanical_tilt_deg: 'Mechanical_Tilt',
  horizontal_beamwidth_deg: 'Horizontal_Beamwidth',
  vertical_beamwidth_deg: 'Vertical_Beamwidth',
}

/** Reverse map: canonical name -> API field name. */
const PROV_TO_API: Record<string, string> = Object.fromEntries(
  Object.entries(API_TO_PROV).map(([k, v]) => [v, k]),
)

interface FieldStats {
  gov: number
  estimated: number
  missing: number
  total: number
}

function classifyOrigin(origin: string): 'gov' | 'estimated' | 'missing' {
  if (!origin || origin === 'missing') return 'missing'
  if (origin.startsWith('est:')) return 'estimated'
  return 'gov'
}

function computeFieldStats(
  basestations: BaseStationData[],
  field: string,
): FieldStats {
  const apiField = PROV_TO_API[field] ?? field
  let gov = 0
  let estimated = 0
  let missing = 0

  for (const bs of basestations) {
    // Try provenance_sources first (flat map), then provenance (nested map)
    let origin = 'missing'
    if (bs.provenance_sources) {
      origin = bs.provenance_sources[apiField] ?? 'missing'
    } else if (bs.provenance) {
      const entry = bs.provenance[apiField]
      origin = entry ? entry.origin : 'missing'
    }

    const cls = classifyOrigin(origin)
    if (cls === 'gov') gov++
    else if (cls === 'estimated') estimated++
    else missing++
  }

  return { gov, estimated, missing, total: basestations.length }
}

function getDominantSourceTag(basestations: BaseStationData[]): string | null {
  const counts: Record<string, number> = {}

  for (const bs of basestations) {
    const prov = bs.provenance_sources ?? (bs.provenance
      ? Object.fromEntries(Object.entries(bs.provenance).map(([k, v]) => [k, v.origin]))
      : null)
    if (!prov) continue

    for (const origin of Object.values(prov)) {
      if (typeof origin === 'string' && origin.startsWith('gov:')) {
        counts[origin] = (counts[origin] ?? 0) + 1
      }
    }
  }

  const entries = Object.entries(counts)
  if (entries.length === 0) return null
  entries.sort((a, b) => b[1] - a[1])
  return entries[0][0]
}

function CompletionBar({ stats }: { stats: FieldStats }) {
  if (stats.total === 0) return null
  const govPct = (stats.gov / stats.total) * 100
  const estPct = (stats.estimated / stats.total) * 100
  const missingPct = (stats.missing / stats.total) * 100

  return (
    <div className="flex h-1.5 rounded-full overflow-hidden bg-muted/50 w-full">
      {govPct > 0 && (
        <div
          className="h-full"
          style={{ width: `${govPct}%`, backgroundColor: '#22c55e' }}
          title={`Government: ${stats.gov} (${govPct.toFixed(0)}%)`}
        />
      )}
      {estPct > 0 && (
        <div
          className="h-full"
          style={{ width: `${estPct}%`, backgroundColor: '#eab308' }}
          title={`Estimated: ${stats.estimated} (${estPct.toFixed(0)}%)`}
        />
      )}
      {missingPct > 0 && (
        <div
          className="h-full"
          style={{ width: `${missingPct}%`, backgroundColor: '#6b7280' }}
          title={`Missing: ${stats.missing} (${missingPct.toFixed(0)}%)`}
        />
      )}
    </div>
  )
}

interface RegionDataCardProps {
  basestations: BaseStationData[]
}

export default function RegionDataCard({ basestations }: RegionDataCardProps) {
  const [collapsed, setCollapsed] = useState(false)

  const { sourceInfo, license, regionName, fieldStats } = useMemo(() => {
    const tag = getDominantSourceTag(basestations)
    const info = tag ? SOURCE_URLS[tag] ?? null : null
    const lic = tag ? SOURCE_LICENSES[tag] ?? null : null
    const region = tag ? SOURCE_REGION_NAMES[tag] ?? (info?.label ?? 'Unknown region') : 'Unknown region'

    const stats: Record<string, FieldStats> = {}
    for (const field of PROVENANCE_FIELDS) {
      stats[field] = computeFieldStats(basestations, field)
    }

    return {
      sourceInfo: info,
      license: lic,
      regionName: region,
      fieldStats: stats,
    }
  }, [basestations])

  // Do not render when there is no provenance data at all
  const hasAnyProvenance = basestations.some(bs => bs.provenance_sources || bs.provenance)
  if (!hasAnyProvenance) return null

  return (
    <div className="mt-3 p-2.5 rounded border border-border bg-muted/30">
      {/* Header - always visible */}
      <button
        className="flex items-center gap-1.5 w-full text-left cursor-pointer"
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed
          ? <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          : <ChevronDown className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
        }
        <span className="text-xs font-medium text-foreground">{regionName}</span>
        <span className="text-[10px] text-muted-foreground ml-auto">Data quality</span>
      </button>

      {!collapsed && (
        <div className="mt-2">
          {/* Source and license info */}
          <div className="flex flex-col gap-1 mb-2.5 text-[10px]">
            {sourceInfo && (
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">Source:</span>
                <a
                  href={sourceInfo.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-400 hover:text-blue-300 flex items-center gap-0.5"
                >
                  {sourceInfo.label}
                  <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
            )}
            {license && (
              <div className="flex items-center gap-1">
                <span className="text-muted-foreground">License:</span>
                <span className="text-foreground">{license}</span>
              </div>
            )}
          </div>

          {/* Per-field completion bars */}
          <div className="space-y-1.5">
            {PROVENANCE_FIELDS.map(field => {
              const stats = fieldStats[field]
              const label = FIELD_LABELS[field] ?? field
              const govPct = stats.total > 0 ? Math.round((stats.gov / stats.total) * 100) : 0

              return (
                <div key={field} className="flex items-center gap-2 text-[10px]">
                  <span className="text-muted-foreground w-10 shrink-0">{label}</span>
                  <div className="flex-1 min-w-0">
                    <CompletionBar stats={stats} />
                  </div>
                  <span className="text-muted-foreground w-8 text-right tabular-nums shrink-0">
                    {govPct}%
                  </span>
                </div>
              )
            })}
          </div>

          {/* Legend */}
          <div className="mt-2 flex items-center gap-2 text-[9px] text-muted-foreground">
            <span className="flex items-center gap-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e] inline-block" /> Gov
            </span>
            <span className="flex items-center gap-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#eab308] inline-block" /> Estimated
            </span>
            <span className="flex items-center gap-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-[#6b7280] inline-block" /> Missing
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
