import { create } from 'zustand'
import * as Sentry from '@sentry/react'
import { fetchWithRetry, parseJsonHeader, fetchCapabilities } from '@/api/client'
import type { ScenePos } from '@/api/coordinates'
import { useSceneStore } from '@/stores/scene'

export type EnvironmentSource = 'none' | 'voxels' | 'osm' | '3dtiles' | 'cesium' | 'coverage'

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
  locationQuery: string
  locationFormatted: string
  radius: number
  geometricError: number
  osmMeshData: EnvironmentMeshData | null
  loading: boolean
  geocoding: boolean
  error: string | null
  osmOptions: OsmOptions
  /** Bumped on every geocode to allow camera re-center on repeated searches */
  geocodeCount: number
  /** @internal AbortController for in-flight environment fetches */
  _abortController: AbortController | null

  setSource: (s: EnvironmentSource) => void
  setLocation: (lat: number, lon: number) => void
  setLocationQuery: (q: string) => void
  setLocationFormatted: (s: string) => void
  setRadius: (r: number) => void
  setGeometricError: (ge: number) => void
  setOsmOptions: (opts: Partial<OsmOptions>) => void
  geocodeAndFetch: (query?: string) => Promise<void>
  reloadAroundPositions: (positions: ScenePos[]) => Promise<void>
  fetchOSM: () => Promise<void>
  fetchGeoJSON: (geojsonStr: string) => Promise<void>
  fetchTilesForRT: () => Promise<void>
  exportForRT: (format: 'differt' | 'sionna') => Promise<string>
}

/** Abort any in-flight environment fetch and return a fresh AbortController. */
function freshAbort(get: () => EnvironmentState, set: (s: Partial<EnvironmentState>) => void): AbortController {
  get()._abortController?.abort()
  const controller = new AbortController()
  set({ _abortController: controller })
  return controller
}

/** Throw an Error with the HTTP status attached when the response is not ok. */
async function throwIfNotOk(resp: Response): Promise<void> {
  if (resp.ok) return
  let msg = `HTTP ${resp.status}`
  try { const err = await resp.json(); msg = err.error || msg } catch {}
  const error = new Error(msg) as Error & { status?: number }
  error.status = resp.status
  throw error
}

/**
 * Report to Sentry unless the error is an intentional abort or a transient
 * upstream-service failure (429/502/503/504). The UI still displays the
 * message either way — external provider hiccups (Overpass, Nominatim,
 * Google 3D Tiles) are not AEGIS bugs, so we don't page on them.
 */
function reportUnexpected(e: unknown): void {
  if ((e as Error).name === 'AbortError') return
  const status = (e as Error & { status?: number }).status
  if (status === 429 || status === 502 || status === 503 || status === 504) return
  Sentry.captureException(e)
}

/**
 * After the backend env_mesh cache has been (re)populated by an environment
 * fetch, pull fresh capabilities so downstream consumers (ray tracing, compute)
 * see has_env_mesh=true. Without this, the RT dispatcher reports "no environment
 * mesh available" even when buildings were loaded successfully.
 */
async function refreshCapabilitiesAfterEnvLoad(): Promise<void> {
  try {
    const caps = await fetchCapabilities()
    useSceneStore.getState().setCapabilities(caps)
  } catch (e) {
    reportUnexpected(e)
  }
}

export const useEnvironmentStore = create<EnvironmentState>((set, get) => ({
  source: 'none',
  location: null,
  locationQuery: '',
  locationFormatted: '',
  radius: 200,
  geometricError: 30,
  osmMeshData: null,
  loading: false,
  geocoding: false,
  error: null,
  osmOptions: {
    defaultBuildingHeight: 10,
    levelHeight: 3.0,
    buildings: true,
    roads: true,
    water: true,
    detail: false,
  },
  geocodeCount: 0,
  _abortController: null,

  setSource: (source) => {
    get()._abortController?.abort()
    set({ source, loading: false, error: null, _abortController: null })
  },
  setLocation: (lat, lon) => set({ location: { lat, lon } }),
  setLocationQuery: (q) => set({ locationQuery: q }),
  setLocationFormatted: (s) => set({ locationFormatted: s }),
  setRadius: (radius) => set({ radius }),
  setGeometricError: (geometricError) => set({ geometricError }),
  setOsmOptions: (opts) =>
    set((s) => ({
      osmOptions: { ...s.osmOptions, ...opts },
    })),

  geocodeAndFetch: async (query?: string) => {
    const { source, locationQuery } = get()
    const q = (query ?? locationQuery).trim()
    if (!q) return
    if (source !== 'osm' && source !== '3dtiles' && source !== 'coverage') return

    const controller = freshAbort(get, set)
    set({ geocoding: true, error: null })
    try {
      const resp = await fetchWithRetry(`/api/geocode?q=${encodeURIComponent(q)}`, {
        signal: controller.signal,
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}))
        const error = new Error(data.error || `Geocoding failed: ${resp.status}`) as Error & { status?: number }
        error.status = resp.status
        throw error
      }
      const { lat, lon, formatted } = await resp.json()
      set((s) => ({
        location: { lat, lon },
        locationFormatted: formatted,
        geocoding: false,
        geocodeCount: s.geocodeCount + 1,
      }))

      // Auto-fetch environment after geocoding
      if (source === 'osm') {
        await get().fetchOSM()
      } else if (source === '3dtiles') {
        await get().fetchTilesForRT()
      }
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        set({ geocoding: false })
        return
      }
      reportUnexpected(e)
      set({ error: (e as Error).message, geocoding: false })
    }
  },

  reloadAroundPositions: async (positions: ScenePos[]) => {
    const { location, source } = get()
    if (!location || positions.length === 0) return
    if (source !== 'osm') return

    // Compute centroid of all positions in scene space
    let cx = 0, cz = 0
    for (const [x, , z] of positions) {
      cx += x
      cz += z
    }
    cx /= positions.length
    cz /= positions.length

    // Compute radius to cover all positions + 100m padding
    let maxDist = 0
    for (const [x, , z] of positions) {
      const d = Math.sqrt((x - cx) ** 2 + (z - cz) ** 2)
      if (d > maxDist) maxDist = d
    }
    const newRadius = Math.max(200, Math.min(1000, Math.ceil(maxDist + 100)))

    // Convert scene centroid to lat/lon offset from current origin
    // Scene X = easting (meters), scene Z = -northing (Y-up swap)
    const METERS_PER_DEG_LAT = 111320
    const metersPerDegLon = 111320 * Math.cos((location.lat * Math.PI) / 180)
    const newLat = location.lat + (-cz) / METERS_PER_DEG_LAT
    const newLon = location.lon + cx / metersPerDegLon

    // Preserve the existing human-readable locationFormatted (e.g. "Paris, France").
    // Overwriting it with coord strings produces ugly duplicates like
    // "48.8575, 2.3514 (48.8575, 2.3514)" in the breadcrumb label.
    set({
      location: { lat: newLat, lon: newLon },
      radius: newRadius,
    })

    await get().fetchOSM()
  },

  fetchGeoJSON: async (geojsonStr: string) => {
    const { location, osmOptions } = get()
    const controller = freshAbort(get, set)
    set({ loading: true, error: null })
    try {
      const resp = await fetchWithRetry('/api/environment/geojson', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          geojson: geojsonStr,
          lat: location?.lat ?? 0,
          lon: location?.lon ?? 0,
          detail: osmOptions.detail,
        }),
        signal: controller.signal,
      })
      await throwIfNotOk(resp)
      const meta = parseJsonHeader<Record<string, unknown>>(resp.headers.get('X-Meta'), 'X-Meta')
      const buf = await resp.arrayBuffer()
      const meshData = parseEnvironmentBinary(buf, meta)
      set({ osmMeshData: meshData, loading: false })
      await refreshCapabilitiesAfterEnvLoad()
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        set({ loading: false })
        return
      }
      reportUnexpected(e)
      set({ error: (e as Error).message, loading: false })
    }
  },

  fetchOSM: async () => {
    const { location, radius, osmOptions } = get()
    if (!location) return
    const controller = freshAbort(get, set)
    set({ loading: true, error: null })
    useSceneStore.getState().setSceneGeometry(null)
    useSceneStore.getState().setLoadedScenePath('')
    useSceneStore.getState().setVoxelData(null)
    try {
      const resp = await fetchWithRetry('/api/environment/osm', {
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
        signal: controller.signal,
      })
      await throwIfNotOk(resp)
      const meta = parseJsonHeader<Record<string, unknown>>(resp.headers.get('X-Meta'), 'X-Meta')
      const buf = await resp.arrayBuffer()
      const meshData = parseEnvironmentBinary(buf, meta)
      set({ osmMeshData: meshData, loading: false })
      await refreshCapabilitiesAfterEnvLoad()
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        set({ loading: false })
        return
      }
      reportUnexpected(e)
      set({ error: (e as Error).message, loading: false })
    }
  },

  fetchTilesForRT: async () => {
    const { location, radius, geometricError } = get()
    if (!location) return
    const controller = freshAbort(get, set)
    set({ loading: true, error: null })
    useSceneStore.getState().setSceneGeometry(null)
    useSceneStore.getState().setLoadedScenePath('')
    useSceneStore.getState().setVoxelData(null)
    try {
      const resp = await fetchWithRetry('/api/environment/3dtiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lat: location.lat,
          lon: location.lon,
          radius,
          geometric_error: geometricError,
        }),
        signal: controller.signal,
      })
      await throwIfNotOk(resp)
      const meta = parseJsonHeader<Record<string, unknown>>(resp.headers.get('X-Meta'), 'X-Meta')
      const buf = await resp.arrayBuffer()
      const meshData = parseEnvironmentBinary(buf, meta)
      set({ osmMeshData: meshData, loading: false })
      await refreshCapabilitiesAfterEnvLoad()
    } catch (e) {
      if ((e as Error).name === 'AbortError') {
        set({ loading: false })
        return
      }
      reportUnexpected(e)
      set({ error: (e as Error).message, loading: false })
    }
  },

  exportForRT: async (format) => {
    // Use a dedicated flag to avoid corrupting the shared `loading` state
    // used by environment fetches (fetchOSM, fetchTilesForRT, fetchGeoJSON).
    try {
      const resp = await fetchWithRetry('/api/environment/export-scene', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format }),
      })
      await throwIfNotOk(resp)
      const data = await resp.json()
      return data.scene_path
    } catch (e) {
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

  if (!Number.isFinite(nV) || !Number.isFinite(nT) || nV < 0 || nT < 0) {
    throw new Error(`Invalid environment mesh metadata: n_vertices=${nV}, n_triangles=${nT}`)
  }

  const expectedBytes = nV * 3 * 4 + nT * 3 * 4 + nT * 3 * 4 + nT
  if (buf.byteLength < expectedBytes) {
    throw new Error(
      `Environment mesh buffer too small: got ${buf.byteLength} bytes, expected ${expectedBytes} ` +
      `(${nV} vertices, ${nT} triangles)`
    )
  }

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
