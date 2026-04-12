import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { ScatterplotLayer, SolidPolygonLayer } from '@deck.gl/layers'
import type { Layer } from '@deck.gl/core'
import type { SpatialComplianceResult } from '@/api/client'

// 16-color operator palette (RGBA arrays)
export const OP_COLORS: [number, number, number, number][] = [
  [59, 130, 245, 255],   // blue
  [245, 130, 28, 255],   // orange
  [46, 194, 125, 255],   // green
  [168, 85, 212, 255],   // purple
  [232, 77, 61, 255],    // red
  [26, 189, 207, 255],   // cyan
  [250, 191, 46, 255],   // yellow
  [140, 87, 41, 255],    // brown
  [112, 128, 143, 255],  // gray
  [214, 95, 166, 255],   // pink
  [102, 166, 31, 255],   // lime
  [179, 51, 92, 255],    // crimson
  [77, 77, 204, 255],    // indigo
  [204, 153, 102, 255],  // tan
  [128, 204, 204, 255],  // teal
  [153, 153, 51, 255],   // olive
]

// Plasma-inspired color ramp for heatmap (6 stops)
const HEATMAP_COLOR_RANGE: [number, number, number][] = [
  [13, 8, 135],
  [126, 3, 168],
  [204, 71, 120],
  [248, 149, 64],
  [252, 225, 56],
  [240, 249, 33],
]

export interface CoverageLayerParams {
  siteLats: Float32Array
  siteLons: Float32Array
  siteOpIndices: Uint8Array
  siteTechIndices: Uint8Array
  siteRegionIndices: Uint8Array
  siteAntennaCounts: Uint8Array
  siteCount: number
  zoom: number
  colorMode: 'density' | 'operator' | 'technology' | 'region'
  onSiteHover: (info: any) => void
  onSiteClick: (info: any) => void
}

// Cache heatmap data array to avoid rebuilding 416K objects on every zoom change
let _cachedHeatmapData: { position: [number, number]; weight: number }[] | null = null
let _cachedHeatmapKey: string | null = null

function getHeatmapData(siteLats: Float32Array, siteLons: Float32Array, siteAntennaCounts: Uint8Array, siteCount: number) {
  const key = `${siteLats.byteLength}-${siteCount}`
  if (_cachedHeatmapData && _cachedHeatmapKey === key && _cachedHeatmapData.length === siteCount) {
    return _cachedHeatmapData
  }
  const data: { position: [number, number]; weight: number }[] = new Array(siteCount)
  for (let i = 0; i < siteCount; i++) {
    data[i] = {
      position: [siteLons[i], siteLats[i]],
      weight: siteAntennaCounts[i] || 1,
    }
  }
  _cachedHeatmapData = data
  _cachedHeatmapKey = key
  return data
}

export function buildCoverageLayers(params: CoverageLayerParams) {
  const {
    siteLats, siteLons, siteOpIndices, siteTechIndices, siteRegionIndices,
    siteAntennaCounts, siteCount, zoom, colorMode, onSiteHover, onSiteClick,
  } = params

  // Heatmap opacity: full at zoom<=9, fades to 0 by zoom 13
  const heatmapOpacity = zoom <= 9 ? 0.85 : zoom >= 13 ? 0 : 0.85 * (13 - zoom) / 4

  // Scatter opacity: 0 at zoom<=9, fades to full by zoom 13
  const scatterOpacity = zoom <= 9 ? 0 : zoom >= 13 ? 0.9 : 0.9 * (zoom - 9) / 4

  const layers: Layer[] = []

  if (heatmapOpacity > 0) {
    const heatmapData = getHeatmapData(siteLats, siteLons, siteAntennaCounts, siteCount)

    layers.push(new HeatmapLayer({
      id: 'antenna-heatmap',
      data: heatmapData,
      getPosition: (d: { position: [number, number]; weight: number }) => d.position,
      getWeight: (d: { position: [number, number]; weight: number }) => d.weight,
      radiusPixels: Math.max(15, 80 - zoom * 5),
      intensity: 2 + zoom * 0.3,
      threshold: 0.01,
      colorRange: HEATMAP_COLOR_RANGE,
      aggregation: 'SUM',
      opacity: heatmapOpacity,
      debounceTimeout: 500,
    }))
  }

  // ScatterplotLayer supports {length} with indexed accessors (efficient)
  if (scatterOpacity > 0) {
    layers.push(new ScatterplotLayer({
      id: 'antenna-sites',
      data: { length: siteCount },
      getPosition: (_: unknown, { index }: { index: number }) => [siteLons[index], siteLats[index], 0] as [number, number, number],
      getRadius: 50,
      radiusMinPixels: 3,
      radiusMaxPixels: 15,
      getFillColor: (_: unknown, { index }: { index: number }) => {
        if (colorMode === 'operator') return OP_COLORS[siteOpIndices[index] % OP_COLORS.length]
        if (colorMode === 'technology') return OP_COLORS[siteTechIndices[index] % OP_COLORS.length]
        if (colorMode === 'region') return OP_COLORS[siteRegionIndices[index] % OP_COLORS.length]
        return [59, 130, 245, 220] as [number, number, number, number]
      },
      pickable: true,
      onHover: onSiteHover,
      onClick: onSiteClick,
      opacity: scatterOpacity,
      updateTriggers: {
        getFillColor: [colorMode],
      },
    }))
  }

  return layers
}

// Compliance zone color ramp: green (safe) -> yellow (margin) -> red (exceeded)
function complianceColor(marginDb: number): [number, number, number, number] {
  if (marginDb >= 20) return [74, 222, 128, 100]    // green, low opacity (very safe)
  if (marginDb >= 10) return [74, 222, 128, 140]    // green
  if (marginDb >= 3)  return [250, 204, 21, 150]    // yellow (getting close)
  if (marginDb >= 0)  return [251, 146, 60, 170]    // orange (near limit)
  return [248, 113, 113, 190]                         // red (exceeded)
}

// Cached compliance cells to avoid rebuilding on every render
let _cachedComplianceCells: { polygon: [number, number][]; color: [number, number, number, number] }[] | null = null
let _cachedComplianceKey: string | null = null

export function buildComplianceZoneLayer(data: SpatialComplianceResult | null) {
  if (!data) return []

  const key = `${data.n_lat}-${data.n_lon}-${data.n_stations}`
  if (!_cachedComplianceCells || _cachedComplianceKey !== key) {
    const cells: { polygon: [number, number][]; color: [number, number, number, number] }[] = []
    const { lats, lons, margin_db } = data
    const dLat = lats.length > 1 ? (lats[1] - lats[0]) / 2 : 0.001
    const dLon = lons.length > 1 ? (lons[1] - lons[0]) / 2 : 0.001

    for (let i = 0; i < lats.length; i++) {
      for (let j = 0; j < lons.length; j++) {
        const margin = margin_db[i][j]
        // Skip cells with very high margins (far from any station)
        if (margin >= 40) continue

        const lat = lats[i]
        const lon = lons[j]
        cells.push({
          polygon: [
            [lon - dLon, lat - dLat],
            [lon + dLon, lat - dLat],
            [lon + dLon, lat + dLat],
            [lon - dLon, lat + dLat],
          ],
          color: complianceColor(margin),
        })
      }
    }
    _cachedComplianceCells = cells
    _cachedComplianceKey = key
  }

  return [
    new SolidPolygonLayer({
      id: 'compliance-zone',
      data: _cachedComplianceCells,
      getPolygon: (d: { polygon: [number, number][] }) => d.polygon,
      getFillColor: (d: { color: [number, number, number, number] }) => d.color,
      pickable: false,
      filled: true,
      extruded: false,
    }),
  ]
}
