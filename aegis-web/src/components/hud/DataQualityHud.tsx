import { useMemo } from 'react'
import { useBaseStationsStore } from '@/stores/basestations'
import { useSimulationStore } from '@/stores/simulation'
import type { BaseStationData } from '@/api/basestations'
import {
  type FidelityTier,
  TIER_COLORS,
  TIER_LABELS,
  computeFidelityTier,
  FIELD_LABELS,
} from '@/utils/fidelityTier'

/** Map API field names to provenance field names (same as AntennaDetailPanel) */
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

/** Provenance fields we track for "weakest fields" analysis */
const PROVENANCE_FIELDS = [
  'Power', 'Azimuth', 'CenterHeight', 'Frequency', 'Gain',
  'Electrical_Tilt', 'Mechanical_Tilt', 'Horizontal_Beamwidth',
  'Vertical_Beamwidth', 'Pattern',
] as const
type ProvField = (typeof PROVENANCE_FIELDS)[number]

interface FieldQuality {
  field: ProvField
  label: string
  missing: number
  estimated: number
  total: number
}

/** Build provenance map from a BaseStationData record.
 *  Checks provenance_sources (flat string map) first, then falls back to
 *  provenance (nested object map), matching RegionDataCard logic. */
function buildProvMap(bs: BaseStationData): Record<string, string> | null {
  const hasFlatProv = bs.provenance_sources && Object.keys(bs.provenance_sources).length > 0
  const hasNestedProv = bs.provenance && Object.keys(bs.provenance).length > 0
  if (!hasFlatProv && !hasNestedProv) return null

  const provMap: Record<string, string> = {}
  for (const [apiField, provField] of Object.entries(API_TO_PROV)) {
    if (bs.provenance_sources) {
      provMap[provField] = bs.provenance_sources[apiField] ?? 'missing'
    } else if (bs.provenance) {
      const entry = bs.provenance[apiField]
      provMap[provField] = entry ? entry.origin : 'missing'
    } else {
      provMap[provField] = 'missing'
    }
  }
  provMap['Pattern'] = bs.pattern_source ?? ''
  return provMap
}

/** Resolve the fidelity tier for a single antenna */
function getTier(bs: BaseStationData): FidelityTier {
  if (bs.fidelity_tier) return bs.fidelity_tier
  const provMap = buildProvMap(bs)
  return computeFidelityTier(provMap)
}

interface TierBucket {
  tier: FidelityTier
  count: number
  fraction: number
  label: string
  color: string
}

const TIER_ORDER: FidelityTier[] = ['full', 'spatial', 'geometric', 'bound', 'location_only']

function computeTierDistribution(basestations: BaseStationData[]): TierBucket[] {
  const counts = new Map<FidelityTier, number>()
  for (const bs of basestations) {
    const tier = getTier(bs)
    counts.set(tier, (counts.get(tier) ?? 0) + 1)
  }

  const total = basestations.length || 1
  return TIER_ORDER.map((tier) => ({
    tier,
    count: counts.get(tier) ?? 0,
    fraction: (counts.get(tier) ?? 0) / total,
    label: TIER_LABELS[tier],
    color: TIER_COLORS[tier],
  }))
}

function computeFieldQualities(basestations: BaseStationData[]): FieldQuality[] {
  const qualities: FieldQuality[] = PROVENANCE_FIELDS.map((field) => ({
    field,
    label: FIELD_LABELS[field] ?? field,
    missing: 0,
    estimated: 0,
    total: basestations.length,
  }))

  for (const bs of basestations) {
    const provMap = buildProvMap(bs)
    for (const fq of qualities) {
      if (!provMap) {
        // No provenance data at all -- count as missing
        fq.missing++
        continue
      }
      const src = provMap[fq.field] || 'missing'
      if (src === 'missing' || src === '') fq.missing++
      else if (src.startsWith('est:')) fq.estimated++
      else if (fq.field === 'Pattern' && src === 'synthetic:gaussian') fq.estimated++
    }
  }

  return qualities
}

function Bar({ fraction, color }: { fraction: number; color: string }) {
  const totalBlocks = 27
  const filled = Math.round(fraction * totalBlocks)
  return (
    <span style={{ letterSpacing: '-1px' }}>
      <span style={{ color }}>{'\u2588'.repeat(filled)}</span>
      <span className="text-zinc-700">{'\u2591'.repeat(totalBlocks - filled)}</span>
    </span>
  )
}

function pct(n: number, total: number): string {
  if (total === 0) return '0%'
  return `${Math.round((n / total) * 100)}%`
}

export function DataQualityHud() {
  const basestations = useBaseStationsStore((s) => s.basestations)
  const mode = useSimulationStore((s) => s.mode)

  const tierDistribution = useMemo(
    () => computeTierDistribution(basestations),
    [basestations],
  )

  const fieldQualities = useMemo(
    () => computeFieldQualities(basestations),
    [basestations],
  )

  // Find the weakest fields (highest missing + estimated rates)
  const weakestFields = useMemo(() => {
    return [...fieldQualities]
      .map((fq) => ({
        ...fq,
        imperfectRate: fq.total > 0 ? (fq.missing + fq.estimated) / fq.total : 0,
      }))
      .filter((fq) => fq.imperfectRate > 0.05) // only show fields >5% imperfect
      .sort((a, b) => b.imperfectRate - a.imperfectRate)
      .slice(0, 4)
  }, [fieldQualities])

  // Compute support percentage for current dosimetry mode
  const supportLine = useMemo(() => {
    if (basestations.length === 0) return null
    // Map dosimetry mode to minimum acceptable tier
    // bound mode: any tier works; aggregate: geometric+; spatial: spatial+
    const modeMinTier: Record<string, Set<FidelityTier>> = {
      bound: new Set(['full', 'spatial', 'geometric', 'bound', 'location_only']),
      aggregate: new Set(['full', 'spatial', 'geometric']),
      spatial: new Set(['full', 'spatial']),
    }

    const modeLevelLabel: Record<string, string> = {
      bound: 'Level 0-1',
      aggregate: 'Level 2',
      spatial: 'Level 3+',
    }

    const acceptable = modeMinTier[mode] ?? modeMinTier['aggregate']
    const label = modeLevelLabel[mode] ?? 'Level 2'

    const supported = tierDistribution.reduce((sum, bucket) => {
      if (acceptable.has(bucket.tier)) return sum + bucket.count
      return sum
    }, 0)

    const supportPct = Math.round((supported / basestations.length) * 100)
    return `Current mode (${label}): ${supportPct}% of antennas fully supported`
  }, [basestations.length, tierDistribution, mode])

  if (basestations.length === 0) return null

  return (
    <div className="pointer-events-auto">
      <div
        className="rounded-lg bg-card/90 backdrop-blur-md border border-border p-3
          text-[11px] font-mono text-foreground/90 shadow-lg min-w-[280px] max-w-[320px]"
      >
        {/* Header */}
        <div className="text-[10px] font-semibold tracking-widest text-muted-foreground mb-1">
          DATA QUALITY
        </div>
        <div className="border-t border-border/60 mb-2" />

        {/* Antenna count */}
        <div className="text-foreground/80 mb-2">
          {basestations.length.toLocaleString()} antennas loaded
        </div>

        {/* Fidelity readiness bars */}
        <div className="text-muted-foreground mb-1">Fidelity readiness:</div>
        <div className="space-y-0.5 mb-3">
          {tierDistribution.map((bucket) => (
            <div key={bucket.tier} className="flex items-center gap-1.5">
              <span className="shrink-0 leading-none" style={{ fontSize: '9px' }}>
                <Bar fraction={bucket.fraction} color={bucket.color} />
              </span>
              <span className="text-foreground/70 tabular-nums w-[30px] text-right">
                {pct(bucket.count, basestations.length)}
              </span>
              <span className="text-muted-foreground truncate">{bucket.label}</span>
            </div>
          ))}
        </div>

        {/* Weakest fields */}
        {weakestFields.length > 0 && (
          <>
            <div className="text-muted-foreground mb-1">Weakest fields:</div>
            <div className="space-y-0.5 mb-2">
              {weakestFields.map((fq) => {
                // Show the dominant issue
                if (fq.missing >= fq.estimated) {
                  return (
                    <div key={fq.field} className="flex items-center gap-2">
                      <span className="text-foreground/60 w-[60px]">{fq.label}</span>
                      <span className="text-red-400 tabular-nums w-[30px] text-right">
                        {pct(fq.missing, fq.total)}
                      </span>
                      <span className="text-muted-foreground">missing</span>
                    </div>
                  )
                }
                return (
                  <div key={fq.field} className="flex items-center gap-2">
                    <span className="text-foreground/60 w-[60px]">{fq.label}</span>
                    <span className="text-amber-400 tabular-nums w-[30px] text-right">
                      {pct(fq.estimated, fq.total)}
                    </span>
                    <span className="text-muted-foreground">estimated</span>
                  </div>
                )
              })}
            </div>
          </>
        )}

        {/* Support line */}
        {supportLine && (
          <div className="text-[10px] text-muted-foreground/80 border-t border-border/40 pt-1.5">
            {supportLine}
          </div>
        )}
      </div>
    </div>
  )
}
