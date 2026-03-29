import { useMemo } from 'react'
import { useBaseStationsStore } from '@/stores/basestations'
import type { BaseStationData } from '@/api/basestations'
import PanelAntenna from './PanelAntenna'

const OPERATOR_COLORS: Record<string, string> = {
  Proximus: '#4488ff',
  Orange: '#f97316',
  Telenet: '#22c55e',
  'Citymesh Mobile (Insky)': '#e879f9',
}
const DEFAULT_COLOR = '#a855f7'
const R = 6_371_000

function bsToScenePos(
  bs: BaseStationData,
  origin: { lat: number; lon: number },
): [number, number, number] {
  const dLat = ((bs.latitude - origin.lat) * Math.PI) / 180
  const dLon = ((bs.longitude - origin.lon) * Math.PI) / 180
  const cosLat = Math.cos((origin.lat * Math.PI) / 180)
  const east = R * dLon * cosLat
  const north = R * dLat
  return [east, bs.height_m, -north]
}

interface SiteGroup {
  siteCode: string
  antennas: { bs: BaseStationData; index: number }[]
}

export default function BaseStationMarkers() {
  const basestations = useBaseStationsStore(s => s.basestations)
  const origin = useBaseStationsStore(s => s.origin)
  const enabledOperators = useBaseStationsStore(s => s.enabledOperators)
  const enabledTechnologies = useBaseStationsStore(s => s.enabledTechnologies)
  const selectedIndex = useBaseStationsStore(s => s.selectedIndex)
  const selectAntenna = useBaseStationsStore(s => s.selectAntenna)

  const siteGroups = useMemo(() => {
    if (!origin || basestations.length === 0) return []

    const groups = new Map<string, SiteGroup>()

    basestations.forEach((bs, index) => {
      if (!enabledOperators.has(bs.operator)) return
      if (!enabledTechnologies.has(bs.technology)) return

      const key = bs.site_code
      if (!groups.has(key)) {
        groups.set(key, { siteCode: key, antennas: [] })
      }
      groups.get(key)!.antennas.push({ bs, index })
    })

    for (const group of groups.values()) {
      group.antennas.sort((a, b) => {
        const azDiff = a.bs.azimuth_deg - b.bs.azimuth_deg
        if (azDiff !== 0) return azDiff
        return a.bs.freq_mhz - b.bs.freq_mhz
      })
    }

    return Array.from(groups.values())
  }, [basestations, origin, enabledOperators, enabledTechnologies])

  if (!origin) return null

  const VERTICAL_GAP = 0.1

  return (
    <group>
      {siteGroups.map(site => {
        const azimuthOffsets = new Map<number, number>()

        return (
          <group key={site.siteCode}>
            {site.antennas.map(({ bs, index }) => {
              const pos = bsToScenePos(bs, origin)
              const azKey = bs.azimuth_deg
              const offset = azimuthOffsets.get(azKey) ?? 0
              azimuthOffsets.set(azKey, offset + 1)
              const verticalShift = offset * ((bs.panel_height_m || 0.3) + VERTICAL_GAP)

              return (
                <PanelAntenna
                  key={index}
                  nH={bs.n_h ?? 2}
                  nV={bs.n_v ?? 4}
                  panelWidth={bs.panel_width_m ?? 0.3}
                  panelHeight={bs.panel_height_m ?? 1.0}
                  azimuthDeg={bs.azimuth_deg}
                  tiltDeg={bs.total_tilt_deg}
                  position={[pos[0], pos[1] + verticalShift, pos[2]]}
                  color={OPERATOR_COLORS[bs.operator] ?? DEFAULT_COLOR}
                  selected={selectedIndex === index}
                  onClick={() => selectAntenna(
                    selectedIndex === index ? null : index,
                  )}
                />
              )
            })}
          </group>
        )
      })}
    </group>
  )
}
