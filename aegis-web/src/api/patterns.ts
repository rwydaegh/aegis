export interface PatternSearchResult {
  id: string
  source: 'local' | 'cloudrf'
  manufacturer: string
  model: string
  frequency_mhz: number
  gain_dbi: number
  tilt_deg: number | null
}

export async function searchPatterns(params: {
  q?: string
  manufacturer?: string
  freq_min?: number
  freq_max?: number
  source?: string
  limit?: number
}): Promise<{ results: PatternSearchResult[] }> {
  const qs = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v != null) qs.set(k, String(v))
  }
  const res = await fetch(`/api/patterns/search?${qs}`)
  if (!res.ok) throw new Error(`Pattern search failed: ${res.status}`)
  return res.json()
}

export interface PatternMeta {
  id: string
  source: string
  max_gain_dbi: number
  shape: [number, number]
}

export async function loadPattern(
  source: string,
  id: string,
): Promise<{ data: Float32Array; meta: PatternMeta }> {
  const res = await fetch(`/api/patterns/${source}/${id}`)
  if (!res.ok) throw new Error(`Pattern load failed: ${res.status}`)
  const metaHeader = res.headers.get('X-Meta')
  const meta: PatternMeta = metaHeader
    ? JSON.parse(metaHeader)
    : { id, source, max_gain_dbi: 0, shape: [181, 360] }
  const buf = await res.arrayBuffer()
  const data = new Float32Array(buf)
  if (data.length !== meta.shape[0] * meta.shape[1]) {
    throw new Error(`Pattern data length ${data.length} does not match shape ${meta.shape}`)
  }
  return { data, meta }
}
