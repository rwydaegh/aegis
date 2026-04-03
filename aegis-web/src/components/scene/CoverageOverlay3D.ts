import {
  Viewer,
  Cartesian3,
  Color,
  NearFarScalar,
  DistanceDisplayCondition,
  LabelStyle,
  PointPrimitiveCollection,
  LabelCollection,
} from 'cesium'
import type { RegionSummary } from '@/api/types'

// 16-color operator palette
const OP_COLORS: Color[] = [
  new Color(0.23, 0.51, 0.96, 1),
  new Color(0.96, 0.51, 0.11, 1),
  new Color(0.18, 0.76, 0.49, 1),
  new Color(0.66, 0.33, 0.83, 1),
  new Color(0.91, 0.30, 0.24, 1),
  new Color(0.10, 0.74, 0.81, 1),
  new Color(0.98, 0.75, 0.18, 1),
  new Color(0.55, 0.34, 0.16, 1),
  new Color(0.44, 0.50, 0.56, 1),
  new Color(0.84, 0.37, 0.65, 1),
  new Color(0.40, 0.65, 0.12, 1),
  new Color(0.70, 0.20, 0.36, 1),
  new Color(0.30, 0.30, 0.80, 1),
  new Color(0.80, 0.60, 0.40, 1),
  new Color(0.50, 0.80, 0.80, 1),
  new Color(0.60, 0.60, 0.20, 1),
]

function completenessColor(c: number): Color {
  if (c > 0.8) return Color.fromCssColorString('#22c55e')
  if (c > 0.4) return Color.fromCssColorString('#f59e0b')
  return Color.fromCssColorString('#ef4444')
}

export interface CoverageOverlayHandle {
  points: PointPrimitiveCollection
  labels: LabelCollection
  destroy: () => void
  setVisible: (v: boolean) => void
}

export function addCoverageOverlay(
  viewer: Viewer,
  siteLats: Float32Array,
  siteLons: Float32Array,
  siteOpIndices: Uint8Array,
  siteCount: number,
  regions: RegionSummary[],
): CoverageOverlayHandle {
  // Site points
  const points = viewer.scene.primitives.add(new PointPrimitiveCollection())
  for (let i = 0; i < siteCount; i++) {
    points.add({
      position: Cartesian3.fromDegrees(siteLons[i], siteLats[i], 100),
      pixelSize: 6,
      color: OP_COLORS[siteOpIndices[i] % OP_COLORS.length],
      scaleByDistance: new NearFarScalar(1e3, 2.0, 1e7, 0.5),
      translucencyByDistance: new NearFarScalar(1e3, 1.0, 1e7, 0.3),
    })
  }

  // Region boundary lines via entities (more reliable API than PolylineCollection)
  const regionEntities: ReturnType<typeof viewer.entities.add>[] = []
  for (const region of regions) {
    if (!region.bbox) continue
    const [minLon, maxLon, minLat, maxLat] = region.bbox
    regionEntities.push(viewer.entities.add({
      polyline: {
        positions: Cartesian3.fromDegreesArray([
          minLon, minLat,
          maxLon, minLat,
          maxLon, maxLat,
          minLon, maxLat,
          minLon, minLat,
        ]),
        width: 2,
        material: completenessColor(region.completeness),
        distanceDisplayCondition: new DistanceDisplayCondition(2e5, Infinity),
      },
    }))
  }

  // Region labels
  const labels = viewer.scene.primitives.add(new LabelCollection())
  for (const region of regions) {
    if (!region.bbox) continue
    const [minLon, maxLon, minLat, maxLat] = region.bbox
    labels.add({
      position: Cartesian3.fromDegrees(
        (minLon + maxLon) / 2,
        (minLat + maxLat) / 2,
        5000,
      ),
      text: `${region.label}\n${region.count.toLocaleString()} antennas`,
      font: '14px sans-serif',
      fillColor: Color.WHITE,
      outlineColor: Color.BLACK,
      outlineWidth: 2,
      style: LabelStyle.FILL_AND_OUTLINE,
      distanceDisplayCondition: new DistanceDisplayCondition(5e5, Infinity),
      scaleByDistance: new NearFarScalar(5e5, 1.0, 5e6, 0.3),
    })
  }

  return {
    points,
    labels,
    destroy: () => {
      viewer.scene.primitives.remove(points)
      viewer.scene.primitives.remove(labels)
      for (const entity of regionEntities) {
        viewer.entities.remove(entity)
      }
    },
    setVisible: (v: boolean) => {
      points.show = v
      labels.show = v
      for (const entity of regionEntities) {
        entity.show = v
      }
    },
  }
}
