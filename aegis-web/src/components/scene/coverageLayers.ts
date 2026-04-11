import { HeatmapLayer } from '@deck.gl/aggregation-layers'
import { ScatterplotLayer } from '@deck.gl/layers'

// 16-color operator palette (RGBA arrays)
const OP_COLORS: [number, number, number, number][] = [
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

export function buildCoverageLayers(params: CoverageLayerParams) {
  const {
    siteLats, siteLons, siteOpIndices, siteTechIndices, siteRegionIndices,
    siteAntennaCounts, siteCount, zoom, colorMode, onSiteHover, onSiteClick,
  } = params

  // Heatmap opacity: full at zoom<=8, fades to 0 by zoom 12
  const heatmapOpacity = zoom <= 8 ? 0.8 : zoom >= 12 ? 0 : 0.8 * (12 - zoom) / 4

  // Scatter opacity: 0 at zoom<=8, fades to full by zoom 12
  const scatterOpacity = zoom <= 8 ? 0 : zoom >= 12 ? 0.9 : 0.9 * (zoom - 8) / 4

  const layers: any[] = []

  // HeatmapLayer needs array of objects (does NOT support {length} + indexed accessors)
  if (heatmapOpacity > 0) {
    const heatmapData: { position: [number, number]; weight: number }[] = []
    for (let i = 0; i < siteCount; i++) {
      heatmapData.push({
        position: [siteLons[i], siteLats[i]],
        weight: siteAntennaCounts[i] || 1,
      })
    }

    layers.push(new HeatmapLayer({
      id: 'antenna-heatmap',
      data: heatmapData,
      getPosition: (d: { position: [number, number]; weight: number }) => d.position,
      getWeight: (d: { position: [number, number]; weight: number }) => d.weight,
      radiusPixels: Math.max(15, 50 - zoom * 3),
      intensity: 1 + zoom * 0.3,
      threshold: 0.05,
      colorRange: HEATMAP_COLOR_RANGE,
      aggregation: 'SUM',
      opacity: heatmapOpacity,
      debounceTimeout: 200,
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
