import { create } from 'zustand'

interface TerrainMeshData {
  positions: Float32Array
  indices: Uint32Array
  width: number
  height: number
}

interface TerrainState {
  enabled: boolean
  meshData: TerrainMeshData | null
  loading: boolean
  error: string | null
  setEnabled: (v: boolean) => void
  fetchTerrain: (lat: number, lon: number, radius: number) => Promise<void>
}

function parseTerrainBinary(
  buf: ArrayBuffer,
  meta: Record<string, unknown>,
): TerrainMeshData {
  const nV = meta.n_vertices as number
  const nT = meta.n_triangles as number
  let offset = 0

  const positions = new Float32Array(buf, offset, nV * 3)
  offset += nV * 3 * 4

  const indices = new Uint32Array(buf, offset, nT * 3)

  return {
    positions,
    indices,
    width: meta.width as number,
    height: meta.height as number,
  }
}

export const useTerrainStore = create<TerrainState>((set) => ({
  enabled: false,
  meshData: null,
  loading: false,
  error: null,

  setEnabled: (enabled) => set({ enabled }),

  fetchTerrain: async (lat, lon, radius) => {
    set({ loading: true, error: null })
    try {
      const resp = await fetch('/api/terrain/elevation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat, lon, radius }),
      })
      if (!resp.ok) {
        const err = await resp.json()
        throw new Error((err as { error?: string }).error || `HTTP ${resp.status}`)
      }
      const meta = JSON.parse(resp.headers.get('X-Meta') || '{}') as Record<string, unknown>
      const buf = await resp.arrayBuffer()
      const meshData = parseTerrainBinary(buf, meta)
      set({ meshData, loading: false, enabled: true })
    } catch (e) {
      set({ error: (e as Error).message, loading: false })
    }
  },
}))
