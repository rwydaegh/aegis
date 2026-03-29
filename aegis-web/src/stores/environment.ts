import { create } from 'zustand'
import * as Sentry from '@sentry/react'

export type EnvironmentSource = 'none' | 'voxels' | 'osm' | '3dtiles'

interface OsmOptions {
  defaultBuildingHeight: number
  levelHeight: number
  buildings: boolean
  roads: boolean
  water: boolean
  detail: boolean
}

interface EnvironmentMeshData {
  positions: Float32Array
  indices: Uint32Array
  normals: Float32Array
  materials: Uint8Array
  meta: Record<string, unknown>
}

interface EnvironmentState {
  source: EnvironmentSource
  location: { lat: number; lon: number } | null
  radius: number
  geometricError: number
  osmMeshData: EnvironmentMeshData | null
  loading: boolean
  error: string | null
  osmOptions: OsmOptions

  setSource: (s: EnvironmentSource) => void
  setLocation: (lat: number, lon: number) => void
  setRadius: (r: number) => void
  setGeometricError: (ge: number) => void
  setOsmOptions: (opts: Partial<OsmOptions>) => void
  fetchOSM: () => Promise<void>
  fetchGeoJSON: (geojsonStr: string) => Promise<void>
  fetchTilesForRT: () => Promise<void>
  exportForRT: (format: 'differt' | 'sionna') => Promise<string>
}

export const useEnvironmentStore = create<EnvironmentState>((set, get) => ({
  source: 'none',
  location: null,
  radius: 200,
  geometricError: 30,
  osmMeshData: null,
  loading: false,
  error: null,
  osmOptions: {
    defaultBuildingHeight: 10,
    levelHeight: 3.0,
    buildings: true,
    roads: true,
    water: true,
    detail: false,
  },

  setSource: (source) => set({ source }),
  setLocation: (lat, lon) => set({ location: { lat, lon } }),
  setRadius: (radius) => set({ radius }),
  setGeometricError: (geometricError) => set({ geometricError }),
  setOsmOptions: (opts) =>
    set((s) => ({
      osmOptions: { ...s.osmOptions, ...opts },
    })),

  fetchGeoJSON: async (geojsonStr: string) => {
    const { location, osmOptions } = get()
    set({ loading: true, error: null })
    try {
      const resp = await fetch('/api/environment/geojson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          geojson: geojsonStr,
          lat: location?.lat ?? 0,
          lon: location?.lon ?? 0,
          detail: osmOptions.detail,
        }),
      })
      if (!resp.ok) {
        let msg = `HTTP ${resp.status}`
        try { const err = await resp.json(); msg = err.error || msg } catch {}
        throw new Error(msg)
      }
      const meta = JSON.parse(resp.headers.get('X-Meta') || '{}')
      const buf = await resp.arrayBuffer()
      const meshData = parseEnvironmentBinary(buf, meta)
      set({ osmMeshData: meshData, loading: false })
    } catch (e) {
      Sentry.captureException(e)
      set({ error: (e as Error).message, loading: false })
    }
  },

  fetchOSM: async () => {
    const { location, radius, osmOptions } = get()
    if (!location) return
    set({ loading: true, error: null })
    try {
      const resp = await fetch('/api/environment/osm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: location.lat,
          lon: location.lon,
          radius,
          detail: osmOptions.detail,
          options: {
            default_building_height: osmOptions.defaultBuildingHeight,
            level_height: osmOptions.levelHeight,
            buildings: osmOptions.buildings,
            roads: osmOptions.roads,
            water: osmOptions.water,
          },
        }),
      })
      if (!resp.ok) {
        let msg = `HTTP ${resp.status}`
        try { const err = await resp.json(); msg = err.error || msg } catch {}
        throw new Error(msg)
      }
      const meta = JSON.parse(resp.headers.get('X-Meta') || '{}')
      const buf = await resp.arrayBuffer()
      const meshData = parseEnvironmentBinary(buf, meta)
      set({ osmMeshData: meshData, loading: false })
    } catch (e) {
      Sentry.captureException(e)
      set({ error: (e as Error).message, loading: false })
    }
  },

  fetchTilesForRT: async () => {
    const { location, radius, geometricError } = get()
    if (!location) return
    set({ loading: true, error: null })
    try {
      const resp = await fetch('/api/environment/3dtiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: location.lat,
          lon: location.lon,
          radius,
          geometric_error: geometricError,
        }),
      })
      if (!resp.ok) {
        let msg = `HTTP ${resp.status}`
        try { const err = await resp.json(); msg = err.error || msg } catch {}
        throw new Error(msg)
      }
      set({ loading: false })
    } catch (e) {
      Sentry.captureException(e)
      set({ error: (e as Error).message, loading: false })
    }
  },

  exportForRT: async (format) => {
    set({ loading: true })
    try {
      const resp = await fetch('/api/environment/export-scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format }),
      })
      if (!resp.ok) {
        let msg = `HTTP ${resp.status}`
        try { const err = await resp.json(); msg = err.error || msg } catch {}
        throw new Error(msg)
      }
      const data = await resp.json()
      set({ loading: false })
      return data.scene_path
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },
}))

function parseEnvironmentBinary(
  buf: ArrayBuffer,
  meta: Record<string, unknown>,
): EnvironmentMeshData {
  const nV = meta.n_vertices as number
  const nT = meta.n_triangles as number
  let offset = 0

  const positions = new Float32Array(buf, offset, nV * 3)
  offset += nV * 3 * 4

  const indices = new Uint32Array(buf, offset, nT * 3)
  offset += nT * 3 * 4

  const normals = new Float32Array(buf, offset, nT * 3)
  offset += nT * 3 * 4

  const materials = new Uint8Array(buf, offset, nT)

  return { positions, indices, normals, materials, meta }
}
