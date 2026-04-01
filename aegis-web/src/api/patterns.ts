import { fetchWithRetry } from './client'

export interface PatternSearchResult {
  manufacturer: string
  model: string
  frequency_mhz: number
  id: string
}

interface SearchResponse {
  results: PatternSearchResult[]
  total: number
}

export async function getManufacturers(): Promise<string[]> {
  const res = await fetchWithRetry('/api/patterns/manufacturers')
  if (!res.ok) throw new Error(`GET /api/patterns/manufacturers failed: ${res.status}`)
  const data = await res.json()
  return data.manufacturers
}

export async function searchPatterns(
  query: string,
  manufacturer?: string,
  freqMhz?: number,
): Promise<SearchResponse> {
  const params = new URLSearchParams()
  if (query) params.set('q', query)
  if (manufacturer) params.set('manufacturer', manufacturer)
  if (freqMhz) params.set('freq_mhz', String(freqMhz))
  const res = await fetchWithRetry(`/api/patterns/search?${params}`)
  if (!res.ok) throw new Error(`GET /api/patterns/search failed: ${res.status}`)
  return res.json()
}
