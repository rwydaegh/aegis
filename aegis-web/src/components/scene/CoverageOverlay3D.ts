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
import type { RegionSummary, ClusterPoint } from '@/api/types'

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

export interface CoverageOverlayHandle {
  labels: LabelCollection
  clusters: PointPrimitiveCollection
  points: PointPrimitiveCollection
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
  clusters: ClusterPoint[],
): CoverageOverlayHandle {
  // --- Tier 1: Region labels (global zoom, 400km-20,000km) ---
  const labels = viewer.scene.primitives.add(new LabelCollection())
  for (const region of regions) {
    if (!region.bbox) continue
    const [minLon, maxLon, minLat, maxLat] = region.bbox
    labels.add({
      position: Cartesian3.fromDegrees(
        (minLon + maxLon) / 2,
        (minLat + maxLat) / 2,
        50_000,
      ),
      text: `${region.label}\n${region.count.toLocaleString()}`,
      font: 'bold 15px sans-serif',
      fillColor: Color.WHITE,
      outlineColor: Color.BLACK,
      outlineWidth: 2,
      style: LabelStyle.FILL_AND_OUTLINE,
      distanceDisplayCondition: new DistanceDisplayCondition(4e5, 2e7),
      scaleByDistance: new NearFarScalar(5e5, 1.0, 8e6, 0.4),
    })
  }

  // --- Tier 2: Cluster points (continental zoom, 40km-600km) ---
  const clusterPoints = viewer.scene.primitives.add(new PointPrimitiveCollection())
  const clusterOps = new Map<string, number>()
  let opIdx = 0
  for (const c of clusters) {
    if (!clusterOps.has(c.operator)) clusterOps.set(c.operator, opIdx++)
  }
  for (const c of clusters) {
    const colorIdx = clusterOps.get(c.operator) ?? 0
    clusterPoints.add({
      position: Cartesian3.fromDegrees(c.lon, c.lat, 200),
      pixelSize: Math.min(6 + Math.log10(Math.max(c.count, 1)) * 8, 28),
      color: OP_COLORS[colorIdx % OP_COLORS.length],
      distanceDisplayCondition: new DistanceDisplayCondition(4e4, 6e5),
      scaleByDistance: new NearFarScalar(5e4, 1.5, 5e5, 0.6),
      translucencyByDistance: new NearFarScalar(5e4, 1.0, 5e5, 0.5),
    })
  }

  // --- Tier 3: Individual site points (local zoom, 0-80km) ---
  const points = viewer.scene.primitives.add(new PointPrimitiveCollection())
  for (let i = 0; i < siteCount; i++) {
    points.add({
      position: Cartesian3.fromDegrees(siteLons[i], siteLats[i], 100),
      pixelSize: 6,
      color: OP_COLORS[siteOpIndices[i] % OP_COLORS.length],
      distanceDisplayCondition: new DistanceDisplayCondition(0, 8e4),
      scaleByDistance: new NearFarScalar(1e3, 2.0, 6e4, 0.5),
      translucencyByDistance: new NearFarScalar(1e3, 1.0, 6e4, 0.4),
    })
  }

  return {
    labels,
    clusters: clusterPoints,
    points,
    destroy: () => {
      viewer.scene.primitives.remove(labels)
      viewer.scene.primitives.remove(clusterPoints)
      viewer.scene.primitives.remove(points)
    },
    setVisible: (v: boolean) => {
      labels.show = v
      clusterPoints.show = v
      points.show = v
    },
  }
}
