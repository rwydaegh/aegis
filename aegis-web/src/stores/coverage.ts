import { create } from 'zustand'
import { fetchCoverage, decodeSitesBinary } from '@/api/coverage'
import type { RegionSummary } from '@/api/types'

interface CoverageState {
  enabled: boolean
  loaded: boolean
  loading: boolean
  error: string | null
  regions: RegionSummary[]
  siteLats: Float32Array | null
  siteLons: Float32Array | null
  siteOpIndices: Uint8Array | null
  siteTechIndices: Uint8Array | null
  siteRegionIndices: Uint8Array | null
  siteAntennaCounts: Uint8Array | null
  siteCount: number
  operatorNames: string[]
  technologyNames: string[]
  regionNames: string[]
  cameraLatLon: { lat: number; lon: number } | null
  zoom: number
  hoveredSiteIndex: number | null
  hoveredScreenCoords: { x: number; y: number } | null
  selectedSiteIndex: number | null
  colorMode: 'density' | 'operator' | 'technology' | 'region'

  fetch: () => Promise<void>
  retry: () => Promise<void>
  setEnabled: (v: boolean) => void
  setCameraLatLon: (ll: { lat: number; lon: number }) => void
  setZoom: (zoom: number) => void
  setHoveredSiteIndex: (index: number | null) => void
  setHoveredScreenCoords: (coords: { x: number; y: number } | null) => void
  setSelectedSiteIndex: (index: number | null) => void
  setColorMode: (mode: 'density' | 'operator' | 'technology' | 'region') => void
}

export const useCoverageStore = create<CoverageState>((set, get) => ({
  enabled: false,
  loaded: false,
  loading: false,
  error: null,
  regions: [],
  siteLats: null,
  siteLons: null,
  siteOpIndices: null,
  siteTechIndices: null,
  siteRegionIndices: null,
  siteAntennaCounts: null,
  siteCount: 0,
  operatorNames: [],
  technologyNames: [],
  regionNames: [],
  cameraLatLon: null,
  zoom: 3,
  hoveredSiteIndex: null,
  hoveredScreenCoords: null,
  selectedSiteIndex: null,
  colorMode: 'density',

  fetch: async () => {
    if (get().loaded || get().loading) return
    set({ loading: true, error: null })
    try {
      const data = await fetchCoverage()
      const { latitudes, longitudes, opIndices, techIndices, regionIndices, antennaCounts } = decodeSitesBinary(
        data.sites_b64,
        data.sites_meta.count,
      )

      set({
        regions: data.regions,
        siteLats: latitudes,
        siteLons: longitudes,
        siteOpIndices: opIndices,
        siteTechIndices: techIndices,
        siteRegionIndices: regionIndices,
        siteAntennaCounts: antennaCounts,
        siteCount: data.sites_meta.count,
        operatorNames: data.sites_meta.operators,
        technologyNames: data.sites_meta.technologies,
        regionNames: data.sites_meta.region_names,
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
  setZoom: (zoom) => set({ zoom }),
  setHoveredSiteIndex: (index) => set({ hoveredSiteIndex: index }),
  setHoveredScreenCoords: (coords) => set({ hoveredScreenCoords: coords }),
  setSelectedSiteIndex: (index) => set({ selectedSiteIndex: index }),
  setColorMode: (mode) => set({ colorMode: mode }),
}))
