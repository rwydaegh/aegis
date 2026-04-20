import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { fetchPathContributions } from '../client'

const _origFetch = globalThis.fetch

function mockJsonResponse(payload: unknown, status = 200): typeof globalThis.fetch {
  return vi.fn(async () =>
    new Response(JSON.stringify(payload), {
      status,
      headers: { 'content-type': 'application/json' },
    }),
  ) as unknown as typeof globalThis.fetch
}

describe('fetchPathContributions', () => {
  let calls: string[] = []

  beforeEach(() => {
    calls = []
  })

  afterEach(() => {
    globalThis.fetch = _origFetch
  })

  it('builds a URL without query params when none are passed', async () => {
    const mock = vi.fn(async (url: string) => {
      calls.push(url)
      return new Response(
        JSON.stringify({
          triangle_index: 0,
          sab_total: 1.0,
          paths: [],
          importance: { top: [], p_abs_total: 0, n_paths: 0 },
          n_paths: 0,
          n_los: 0,
          n_nlos: 0,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      )
    })
    globalThis.fetch = mock as unknown as typeof globalThis.fetch

    await fetchPathContributions()
    expect(calls).toHaveLength(1)
    expect(calls[0]).toBe('/api/analyze/path-contributions')
  })

  it('passes top_k and triangle_index through as query parameters', async () => {
    const mock = vi.fn(async (url: string) => {
      calls.push(url)
      return new Response(
        JSON.stringify({
          triangle_index: 42,
          sab_total: 1.0,
          paths: [],
          importance: { top: [], p_abs_total: 0, n_paths: 0 },
          n_paths: 0,
          n_los: 0,
          n_nlos: 0,
        }),
        { status: 200, headers: { 'content-type': 'application/json' } },
      )
    })
    globalThis.fetch = mock as unknown as typeof globalThis.fetch

    await fetchPathContributions({ top_k: 5, triangle_index: 42 })
    expect(calls[0]).toContain('top_k=5')
    expect(calls[0]).toContain('triangle_index=42')
  })

  it('returns parsed JSON on 200', async () => {
    const payload = {
      triangle_index: 7,
      sab_total: 12.5,
      paths: [
        {
          index: 0,
          contribution_w_m2: 10,
          fraction: 0.8,
          cumulative: 0.8,
          k_hat: [1, 0, 0],
          power_w_m2: 1000,
          is_los: true,
        },
      ],
      importance: {
        top: [{ index: 0, importance_w: 1, fraction: 0.9, is_los: true }],
        p_abs_total: 1.1,
        n_paths: 1,
      },
      n_paths: 1,
      n_los: 1,
      n_nlos: 0,
    }
    globalThis.fetch = mockJsonResponse(payload)
    const result = await fetchPathContributions({ top_k: 5 })
    expect(result.triangle_index).toBe(7)
    expect(result.paths).toHaveLength(1)
    expect(result.paths[0].is_los).toBe(true)
    expect(result.importance.n_paths).toBe(1)
  })

  it('throws when the server returns an error status', async () => {
    globalThis.fetch = mockJsonResponse({ error: 'no cache' }, 404)
    await expect(fetchPathContributions()).rejects.toThrow()
  })
})
