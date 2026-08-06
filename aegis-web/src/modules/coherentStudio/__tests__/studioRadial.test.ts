import { describe, it, expect } from 'vitest'
import { radialProfile, reliableRadius, type VolumeGrid } from '../panels/studioRadial'

// A small isotropic grid centred on the origin: 5^3 voxels, 0.1 m pitch, so
// centres run -0.2 .. +0.2 on each axis and the focus at the centre is fully
// enclosed by a sphere of radius 0.2 m (the nearest face).
function centredGrid(fill: (x: number, y: number, z: number) => number): VolumeGrid {
  const n = 5
  const spacing = 0.1
  const origin: [number, number, number] = [-0.2, -0.2, -0.2]
  const scalar = new Float32Array(n * n * n)
  let idx = 0
  for (let i = 0; i < n; i++)
    for (let j = 0; j < n; j++)
      for (let k = 0; k < n; k++) {
        scalar[idx++] = fill(origin[0] + i * spacing, origin[1] + j * spacing, origin[2] + k * spacing)
      }
  return { scalar, shape: [n, n, n], origin, spacing }
}

describe('reliableRadius', () => {
  it('is the distance to the nearest box face for a centred focus', () => {
    const grid = centredGrid(() => 1)
    expect(reliableRadius(grid, [0, 0, 0])).toBeCloseTo(0.2, 6)
  })
  it('shrinks for an off-centre focus', () => {
    const grid = centredGrid(() => 1)
    // Focus pushed +0.1 in x: nearest face is the +x face at 0.2, so 0.1 m away.
    expect(reliableRadius(grid, [0.1, 0, 0])).toBeCloseTo(0.1, 6)
  })
  it('clamps to zero for a focus outside the box', () => {
    const grid = centredGrid(() => 1)
    expect(reliableRadius(grid, [5, 0, 0])).toBe(0)
  })
})

describe('radialProfile', () => {
  it('recovers a monotone decay: inner shells exceed outer shells', () => {
    // Field falls off as 1 / (1 + r): peak at the focus, decaying outward.
    const grid = centredGrid((x, y, z) => 1 / (1 + Math.sqrt(x * x + y * y + z * z)))
    const prof = radialProfile(grid, [0, 0, 0], 8)
    expect(prof.bins.length).toBeGreaterThan(1)
    for (let i = 1; i < prof.bins.length; i++) {
      expect(prof.bins[i].median).toBeLessThanOrEqual(prof.bins[i - 1].median + 1e-9)
    }
  })
  it('reports a non-negative IQR band equal to p75 - p25', () => {
    const grid = centredGrid((x, y, z) => Math.abs(x) + Math.abs(y) + Math.abs(z))
    const prof = radialProfile(grid, [0, 0, 0], 6)
    for (const b of prof.bins) {
      expect(b.band).toBeGreaterThanOrEqual(0)
      expect(b.band).toBeCloseTo(b.p75 - b.p25, 9)
    }
  })
  it('puts the focus voxel in the first shell with the peak value', () => {
    const grid = centredGrid((x, y, z) => (x === 0 && y === 0 && z === 0 ? 10 : 1))
    const prof = radialProfile(grid, [0, 0, 0], 8)
    expect(prof.bins[0].median).toBe(10)
  })
  it('returns no bins for an empty / degenerate grid', () => {
    const grid: VolumeGrid = { scalar: new Float32Array(0), shape: [0, 0, 0], origin: [0, 0, 0], spacing: 0.1 }
    expect(radialProfile(grid, [0, 0, 0], 8).bins).toEqual([])
  })
})
