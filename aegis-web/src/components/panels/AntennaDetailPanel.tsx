import { useBaseStationsStore } from '@/stores/basestations'
import ProvenanceDot from './ProvenanceDot'

const FIELD_LABELS: Record<string, string> = {
  eirp_dbm: 'EIRP',
  azimuth_deg: 'Azimuth',
  height_m: 'Height',
  freq_mhz: 'Frequency',
  gain_dbi: 'Gain',
  electrical_tilt_deg: 'E-Tilt',
  mechanical_tilt_deg: 'M-Tilt',
  horizontal_beamwidth_deg: 'H-BW',
  vertical_beamwidth_deg: 'V-BW',
}

const FIELD_UNITS: Record<string, string> = {
  eirp_dbm: 'dBm',
  azimuth_deg: 'deg',
  height_m: 'm',
  freq_mhz: 'MHz',
  gain_dbi: 'dBi',
  electrical_tilt_deg: 'deg',
  mechanical_tilt_deg: 'deg',
  horizontal_beamwidth_deg: 'deg',
  vertical_beamwidth_deg: 'deg',
}

export default function AntennaDetailPanel() {
  const selectedIndex = useBaseStationsStore(s => s.selectedIndex)
  const basestations = useBaseStationsStore(s => s.basestations)
  const selectAntenna = useBaseStationsStore(s => s.selectAntenna)

  if (selectedIndex === null || selectedIndex >= basestations.length) return null

  const bs = basestations[selectedIndex]
  const prov = bs.provenance ?? {}
  const hasProv = Object.keys(prov).length > 0

  const fieldValue = (key: string): string => {
    const val = (bs as unknown as Record<string, unknown>)[key]
    if (val === null || val === undefined) return 'N/A'
    if (typeof val === 'number') return val.toFixed(1)
    return String(val)
  }

  return (
    <div className="mt-3 p-2 rounded border border-border bg-muted/30">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-foreground">
          {bs.operator} - {bs.technology}
        </span>
        <button
          className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          onClick={() => selectAntenna(null)}
        >
          x
        </button>
      </div>

      <div className="text-[10px] text-muted-foreground mb-2">
        {bs.site_code} / {bs.antenna_label}
      </div>

      {bs.frequency_band && (
        <div className="text-xs text-foreground mb-2">{bs.frequency_band}</div>
      )}

      <div className="grid grid-cols-2 gap-x-3 gap-y-1">
        {Object.entries(FIELD_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center text-xs">
            <span className="text-muted-foreground w-12">{label}</span>
            <span className="text-foreground">
              {fieldValue(key)} {FIELD_UNITS[key]}
            </span>
            {hasProv && prov[key] && (
              <ProvenanceDot
                confidence={prov[key].confidence}
                title={`${prov[key].origin} (${(prov[key].confidence * 100).toFixed(0)}%)`}
              />
            )}
          </div>
        ))}
      </div>

      {bs.pattern_source && (
        <div className="text-[10px] text-muted-foreground mt-2">
          Pattern: {bs.pattern_source}
        </div>
      )}

      {hasProv && (
        <div className="text-[10px] text-muted-foreground mt-1">
          Overall confidence: {((bs.confidence ?? 0) * 100).toFixed(0)}%
        </div>
      )}
    </div>
  )
}
