import { create } from 'zustand'
import { fetchCoverage, decodeSitesBinary } from '@/api/coverage'
import type { RegionSummary, ClusterPoint } from '@/api/types'

interface CoverageState {
  enabled: boolean
  loaded: boolean
  loading: boolean
  error: string | null
  regions: RegionSummary[]
  clusters: ClusterPoint[]
  siteLats: Float32Array | null
  siteLons: Float32Array | null
  siteOpIndices: Uint8Array | null
  siteCount: number
  operatorNames: string[]
  technologyNames: string[]
  cameraLatLon: { lat: number; lon: number } | null
  cameraAltitude: number

  fetch: () => Promise<void>
  retry: () => Promise<void>
  setEnabled: (v: boolean) => void
  setCameraLatLon: (ll: { lat: number; lon: number }) => void
  setCameraAltitude: (alt: number) => void
}

export const useCoverageStore = create<CoverageState>((set, get) => ({
  enabled: false,
  loaded: false,
  loading: false,
  error: null,
  regions: [],
  clusters: [],
  siteLats: null,
  siteLons: null,
  siteOpIndices: null,
  siteCount: 0,
  operatorNames: [],
  technologyNames: [],
  cameraLatLon: null,
  cameraAltitude: Infinity,

  fetch: async () => {
    const { loaded, loading } = get()
    if (loaded || loading) return
    set({ loading: true, error: null })
    try {
      const data = await fetchCoverage()
      const { latitudes, longitudes, opIndices } = decodeSitesBinary(
        data.sites_b64,
        data.sites_meta.count,
      )

      set({
        regions: data.regions,
        clusters: data.clusters,
        siteLats: latitudes,
        siteLons: longitudes,
        siteOpIndices: opIndices,
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

  retry: async () => {
    set({ loaded: false, loading: false, error: null })
    await get().fetch()
  },

  setEnabled: (v) => set({ enabled: v }),
  setCameraLatLon: (ll) => set({ cameraLatLon: ll }),
  setCameraAltitude: (alt) => set({ cameraAltitude: alt }),
}))
