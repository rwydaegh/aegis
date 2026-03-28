import { postJson } from './client'
import type { DosimetryStats } from './types'

export interface BaseStationData {
  site_code: string
  antenna_label: string
  operator: string
  technology: string
  latitude: number
  longitude: number
  height_m: number
  eirp_dbm: number
  gain_dbi: number
  freq_mhz: number
  azimuth_deg: number
  total_tilt_deg: number
  has_pattern: boolean
  horizontal_beamwidth_deg: number
  vertical_beamwidth_deg: number
}

interface LoadResponse {
  count: number
  basestations: BaseStationData[]
}

interface LoadParams {
  lat: number
  lon: number
  radius_m?: number
  operator?: string
  technology?: string
}

export async function loadBasestations(params: LoadParams): Promise<LoadResponse> {
  return postJson<LoadResponse>('/api/basestations/load', params)
}

export async function listBasestations(): Promise<LoadResponse> {
  const res = await fetch('/api/basestations/list')
  if (!res.ok) throw new Error(`GET /api/basestations/list failed: ${res.status} ${res.statusText}`)
  return res.json() as Promise<LoadResponse>
}

interface ComputeParams {
  indices?: number[]
  mode?: string
  body_offset?: [number, number, number]
  body_rotation_y?: number
  quantities?: string[]
  skin_model?: string
  freq_hz?: number
}

export interface ComputeResult {
  sab: Float32Array
  stats: DosimetryStats
  arrays: Record<string, Float32Array>
}

export async function computeBasestations(
  params: ComputeParams,
  signal?: AbortSignal,
): Promise<ComputeResult> {
  const res = await fetch('/api/basestations/compute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
    signal,
  })
  if (!res.ok) throw new Error(`POST /api/basestations/compute failed: ${res.status} ${res.statusText}`)

  const statsHeader = res.headers.get('X-Stats')
  if (!statsHeader) throw new Error('POST /api/basestations/compute: missing X-Stats header')
  const stats: DosimetryStats = JSON.parse(statsHeader)

  const buffer = await res.arrayBuffer()

  const arrays: Record<string, Float32Array> = {}
  if (stats.arrays && stats.arrays.length > 0) {
    for (const meta of stats.arrays) {
      const byteOffset = meta.offset
      const byteLength = meta.length * 4
      arrays[meta.key] = new Float32Array(buffer.slice(byteOffset, byteOffset + byteLength))
    }
  } else {
    arrays['sab'] = new Float32Array(buffer)
  }

  return { sab: arrays['sab'] ?? new Float32Array(buffer), stats, arrays }
}
