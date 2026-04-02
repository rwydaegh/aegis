import { create } from 'zustand'
import { fetchCoverage, decodeSitesBinary } from '@/api/coverage'
import { latLonToECEF } from '@/lib/geo'
import type { RegionSummary, ClusterPoint } from '@/api/types'

// Operator colors: consistent palette for up to 16 operators
const OPERATOR_COLORS: [number, number, number][] = [
  [0.23, 0.51, 0.96], // blue
  [0.96, 0.51, 0.11], // orange
  [0.18, 0.76, 0.49], // green
  [0.66, 0.33, 0.83], // purple
  [0.91, 0.30, 0.24], // red
  [0.10, 0.74, 0.81], // cyan
  [0.98, 0.75, 0.18], // yellow
  [0.55, 0.34, 0.16], // brown
  [0.44, 0.50, 0.56], // gray
  [0.84, 0.37, 0.65], // pink
  [0.40, 0.65, 0.12], // lime
  [0.70, 0.20, 0.36], // maroon
  [0.30, 0.30, 0.80], // indigo
  [0.80, 0.60, 0.40], // tan
  [0.50, 0.80, 0.80], // teal
  [0.60, 0.60, 0.20], // olive
]

interface CoverageState {
  enabled: boolean
  loaded: boolean
  loading: boolean
  error: string | null
  regions: RegionSummary[]
  clusters: ClusterPoint[]
  sitePositions: Float32Array | null
  siteColors: Float32Array | null
  siteCount: number
  operatorNames: string[]
  technologyNames: string[]
  activeTier: 1 | 2 | 3
  cameraLatLon: { lat: number; lon: number } | null
  cameraAltitude: number
  hoveredRegion: string | null

  fetch: () => Promise<void>
  setEnabled: (v: boolean) => void
  setActiveTier: (t: 1 | 2 | 3) => void
  setCameraLatLon: (ll: { lat: number; lon: number }) => void
  setCameraAltitude: (alt: number) => void
  setHoveredRegion: (r: string | null) => void
}

export const useCoverageStore = create<CoverageState>((set, get) => ({
  enabled: false,
  loaded: false,
  loading: false,
  error: null,
  regions: [],
  clusters: [],
  sitePositions: null,
  siteColors: null,
  siteCount: 0,
  operatorNames: [],
  technologyNames: [],
  activeTier: 1,
  cameraLatLon: null,
  cameraAltitude: Infinity,
  hoveredRegion: null,

  fetch: async () => {
    if (get().loaded || get().loading) return
    set({ loading: true, error: null })
    try {
      const data = await fetchCoverage()

      // Decode binary sites
      const { latitudes, longitudes, opIndices } = decodeSitesBinary(
        data.sites_b64,
        data.sites_meta.count,
      )

      // Convert to ECEF positions (500m above surface to avoid z-fighting)
      const positions = new Float32Array(data.sites_meta.count * 3)
      const colors = new Float32Array(data.sites_meta.count * 3)
      for (let i = 0; i < data.sites_meta.count; i++) {
        const ecef = latLonToECEF(latitudes[i], longitudes[i], 500)
        positions[i * 3] = ecef.x
        positions[i * 3 + 1] = ecef.y
        positions[i * 3 + 2] = ecef.z

        const color = OPERATOR_COLORS[opIndices[i] % OPERATOR_COLORS.length]
        colors[i * 3] = color[0]
        colors[i * 3 + 1] = color[1]
        colors[i * 3 + 2] = color[2]
      }

      set({
        regions: data.regions,
        clusters: data.clusters,
        sitePositions: positions,
        siteColors: colors,
        siteCount: data.sites_meta.count,
        operatorNames: data.sites_meta.operators,
        technologyNames: data.sites_meta.technologies,
        loaded: true,
        loading: false,
      })
    } catch (err) {
      console.error('Failed to fetch coverage data:', err)
      set({ error: (err as Error).message, loading: false })
    }
  },

  setEnabled: (v) => set({ enabled: v }),
  setActiveTier: (t) => set({ activeTier: t }),
  setCameraLatLon: (ll) => set({ cameraLatLon: ll }),
  setCameraAltitude: (alt) => set({ cameraAltitude: alt }),
  setHoveredRegion: (r) => set({ hoveredRegion: r }),
}))
