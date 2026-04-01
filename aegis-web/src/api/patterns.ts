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

export async function loadPattern(source: string, id: string): Promise<Float32Array> {
  const res = await fetch(`/api/patterns/${source}/${id}`)
  if (!res.ok) throw new Error(`Pattern load failed: ${res.status}`)
  const buf = await res.arrayBuffer()
  return new Float32Array(buf)
}
