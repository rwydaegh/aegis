import { useState } from 'react'
import { useBaseStationsStore } from '@/stores/basestations'
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react'
import type { FidelityTier } from '@/utils/fidelityTier'
import {
  computeFidelityTier,
  computeUpgradePath,
  TIER_COLORS,
  TIER_LABELS,
  TIER_DESCRIPTIONS,
  SOURCE_URLS,
  FIELD_IMPACT,
  FIELD_LABELS,
  FIELD_UNITS,
} from '@/utils/fidelityTier'

// Map API field names to provenance field names
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

function sourceColor(origin: string): string {
  if (origin.startsWith('gov:') || origin === 'ocid') return '#22c55e'
  if (origin.startsWith('est:')) return '#f59e0b'
  if (origin === 'missing') return '#6b7280'
  return '#94a3b8'
}

function sourceLabel(origin: string): string {
  if (origin === 'missing') return 'missing'
  if (origin.startsWith('est:')) return origin.replace('est:', 'est: ')
  const source = SOURCE_URLS[origin]
  if (source) return source.label
  return origin.replace('gov:', '')
}

function ImpactBar({ impact }: { impact: number }) {
  return (
    <span className="inline-flex gap-px ml-1">
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          className="w-1 h-2.5 rounded-sm"
          style={{
            backgroundColor: i <= impact ? '#94a3b8' : '#1e293b',
          }}
        />
      ))}
    </span>
  )
}

function TierBadge({ tier }: { tier: FidelityTier }) {
  return (
    <div
      className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium"
      style={{
        backgroundColor: TIER_COLORS[tier] + '20',
        color: TIER_COLORS[tier],
        border: `1px solid ${TIER_COLORS[tier]}40`,
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: TIER_COLORS[tier] }}
      />
      {TIER_LABELS[tier]}
    </div>
  )
}

export default function AntennaDetailPanel() {
  const selectedIndex = useBaseStationsStore(s => s.selectedIndex)
  const basestations = useBaseStationsStore(s => s.basestations)
  const selectAntenna = useBaseStationsStore(s => s.selectAntenna)
  const [showUpgrade, setShowUpgrade] = useState(false)

  if (selectedIndex === null || selectedIndex >= basestations.length) return null

  const bs = basestations[selectedIndex]
  const prov = bs.provenance ?? {}
  const hasProv = Object.keys(prov).length > 0

  // Build provenance map using parquet-style field names for tier computation
  const provMap: Record<string, string> = {}
  for (const [apiField, provField] of Object.entries(API_TO_PROV)) {
    const p = prov[apiField]
    provMap[provField] = p ? p.origin : 'missing'
  }
  provMap['Pattern'] = bs.pattern_source ?? ''

  const tier: FidelityTier = bs.fidelity_tier ?? computeFidelityTier(hasProv ? provMap : null)
  const upgradePath = computeUpgradePath(hasProv ? provMap : null)

  const fieldValue = (key: string): string => {
    const val = (bs as unknown as Record<string, unknown>)[key]
    if (val === null || val === undefined) return '-'
    if (typeof val === 'number') {
      if (Number.isNaN(val)) return '-'
      return val.toFixed(1)
    }
    return String(val)
  }

  // Find the dominant source for the source link
  const sourceOrigins = Object.values(prov).map(p => p.origin).filter(o => o.startsWith('gov:'))
  const dominantSource = sourceOrigins.length > 0
    ? sourceOrigins.sort((a, b) =>
        sourceOrigins.filter(v => v === b).length - sourceOrigins.filter(v => v === a).length
      )[0]
    : null
  const sourceInfo = dominantSource ? SOURCE_URLS[dominantSource] : null

  // Group fields by tier requirement
  const coreFields = ['eirp_dbm', 'freq_mhz', 'azimuth_deg', 'height_m', 'gain_dbi']
  const tiltFields = ['electrical_tilt_deg', 'mechanical_tilt_deg']
  const beamFields = ['horizontal_beamwidth_deg', 'vertical_beamwidth_deg']

  const renderField = (key: string) => {
    const provField = API_TO_PROV[key]
    const label = FIELD_LABELS[provField] ?? key
    const unit = FIELD_UNITS[provField] ?? ''
    const impact = FIELD_IMPACT[provField] ?? 0
    const p = prov[key]
    const origin = p?.origin ?? 'missing'
    const val = fieldValue(key)

    return (
      <div key={key} className="flex items-center text-xs py-0.5">
        <span className="text-muted-foreground w-10 shrink-0">{label}</span>
        <span className="text-foreground w-16 shrink-0 tabular-nums">
          {val !== '-' ? `${val} ${unit}` : '-'}
        </span>
        {hasProv && (
          <>
            <span
              className="text-[9px] truncate max-w-20"
              style={{ color: sourceColor(origin) }}
              title={origin}
            >
              {sourceLabel(origin)}
            </span>
            <ImpactBar impact={impact} />
          </>
        )}
      </div>
    )
  }

  return (
    <div className="mt-3 p-2.5 rounded border border-border bg-muted/30">
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-foreground">{bs.operator}</span>
          <span className="text-xs text-muted-foreground">{bs.technology}</span>
          {bs.frequency_band && (
            <span className="text-[10px] text-muted-foreground">{bs.frequency_band}</span>
          )}
        </div>
        <button
          className="text-xs text-muted-foreground hover:text-foreground cursor-pointer px-1"
          onClick={() => selectAntenna(null)}
        >
          x
        </button>
      </div>

      <div className="text-[10px] text-muted-foreground mb-2">
        {bs.site_code} / {bs.antenna_label}
      </div>

      {/* Fidelity tier badge */}
      <div className="mb-2.5">
        <TierBadge tier={tier} />
        <div className="text-[10px] text-muted-foreground mt-1">
          {TIER_DESCRIPTIONS[tier]}
        </div>
      </div>

      {/* Field matrix - core fields */}
      <div className="mb-1">
        {coreFields.map(renderField)}
      </div>

      {/* Tilt fields */}
      <div className="border-t border-border/50 pt-1 mb-1">
        <div className="text-[9px] text-muted-foreground/60 mb-0.5">Level 3+ fields</div>
        {tiltFields.map(renderField)}
      </div>

      {/* Beamwidth fields */}
      <div className="border-t border-border/50 pt-1 mb-1">
        <div className="text-[9px] text-muted-foreground/60 mb-0.5">Level 5+ fields</div>
        {beamFields.map(renderField)}
      </div>

      {/* Pattern */}
      <div className="border-t border-border/50 pt-1 text-[10px] text-muted-foreground">
        Pattern: {bs.pattern_source || 'none'}
      </div>

      {/* Source link */}
      {sourceInfo && (
        <div className="mt-1.5 flex items-center gap-1 text-[10px]">
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

      {/* Upgrade path (collapsible) */}
      {upgradePath.length > 0 && (
        <div className="mt-2 border-t border-border/50 pt-1.5">
          <button
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground cursor-pointer w-full"
            onClick={() => setShowUpgrade(!showUpgrade)}
          >
            {showUpgrade ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            What would unlock higher fidelity?
          </button>
          {showUpgrade && (
            <ul className="mt-1 space-y-0.5">
              {upgradePath.map((issue, i) => (
                <li key={i} className="text-[10px] text-muted-foreground pl-4">
                  - {issue}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
