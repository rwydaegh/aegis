import type { CoverageResponse } from './types'

export async function fetchCoverage(): Promise<CoverageResponse> {
  const resp = await fetch('/api/basestations/coverage')
  if (!resp.ok) {
    throw new Error(`Coverage fetch failed: ${resp.status}`)
  }
  return resp.json()
}

/** Decode base64 sites binary into typed arrays. */
export function decodeSitesBinary(
  b64: string,
  count: number,
): { latitudes: Float32Array; longitudes: Float32Array; opIndices: Uint8Array; techIndices: Uint8Array } {
  const raw = Uint8Array.from(atob(b64), c => c.charCodeAt(0))
  const latitudes = new Float32Array(count)
  const longitudes = new Float32Array(count)
  const opIndices = new Uint8Array(count)
  const techIndices = new Uint8Array(count)

  const view = new DataView(raw.buffer)
  for (let i = 0; i < count; i++) {
    const offset = i * 10
    latitudes[i] = view.getFloat32(offset, true)      // little-endian
    longitudes[i] = view.getFloat32(offset + 4, true)
    opIndices[i] = raw[offset + 8]
    techIndices[i] = raw[offset + 9]
  }

  return { latitudes, longitudes, opIndices, techIndices }
}
