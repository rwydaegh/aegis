import { describe, it, expect } from 'vitest'
import {
  computeComplianceFootprint,
  computeComplianceVolume,
  smoothRadii,
  DEFAULT_OBSERVER_HEIGHT_M,
  type FootprintInputs,
  type VolumeInputs,
} from '../complianceFootprint'
import type { AntennaElement } from '../antennaGain'

const ISO_ELEMENT: AntennaElement = { offset: [0, 0, 0], weight: [1, 0], axis: [0, 1, 0] }

// Helper to make a minimal FootprintInputs with sensible defaults.
function makeInputs(partial: Partial<FootprintInputs>): FootprintInputs {
  return {
    antennaRadiatorPos: [0, 2, 0],
    bodyCenterPos: [0, 1.1, 10],
    marginDb: 0,
    patternType: 'isotropic',
    elements: [ISO_ELEMENT],
    nAzimuth: 64,
    ...partial,
  }
}

describe('computeComplianceFootprint — isotropic', () => {
  it('produces a nearly circular ring with margin_db = 0', () => {
    const body = [0, 1.1, 10] as [number, number, number]
    const result = computeComplianceFootprint(
      makeInputs({ bodyCenterPos: body, marginDb: 0 }),
    )
    expect(result.degenerate).toBe(false)
    expect(result.isCircular).toBe(true)
    // Every radius should be close to the body horizontal distance.
    const expectedR = Math.sqrt(10 * 10) // horizontal
    for (let i = 0; i < result.radii.length; i++) {
      expect(result.radii[i]).toBeGreaterThan(0)
      expect(Math.abs(result.radii[i] - expectedR)).toBeLessThan(0.2)
    }
  })

  it('shrinks when margin_db is positive (compliant at body)', () => {
    const bodyAt10 = makeInputs({ bodyCenterPos: [0, 1.1, 10], marginDb: 6 })
    const result = computeComplianceFootprint(bodyAt10)
    // 6 dB compliant means S_body = S_limit / 4, so iso is at half the 3D slant.
    // Horizontal radius ~ sqrt((d/2)² - dh²). With d_body ≈ 10, dh ≈ 0.5, slant/2 ≈ 5.
    expect(result.maxR).toBeLessThan(6)
    expect(result.maxR).toBeGreaterThan(4)
  })

  it('grows when margin_db is negative (noncompliant)', () => {
    const result = computeComplianceFootprint(
      makeInputs({ bodyCenterPos: [0, 1.1, 10], marginDb: -6 }),
    )
    expect(result.maxR).toBeGreaterThan(15)
  })
})

describe('computeComplianceFootprint — height geometry', () => {
  it('degenerates into a tiny ground ring when the antenna towers far above the observer', () => {
    // Body at horizontal 10 m, antenna 50 m up. d_body_3d ≈ sqrt(100 + 48.9²) ≈ 49.9.
    // At margin_db = 0 the iso-sphere has radius 49.9 m, so the horizontal
    // intersection at observer height is sqrt(49.9² - 48.5²) ≈ 11.7 m.
    // But if we bump margin to +6 dB (compliant), scale = 0.5 brings iso-slant
    // to 24.95 m, which is well under dh = 48.5 m — no ground ring at all.
    const result = computeComplianceFootprint(
      makeInputs({
        antennaRadiatorPos: [0, 50, 0],
        bodyCenterPos: [0, 1.1, 10],
        marginDb: 6,
      }),
    )
    expect(result.degenerate).toBe(true)
    expect(result.maxR).toBe(0)
  })

  it('intersects the observer plane as a circle when the iso-sphere is large enough', () => {
    // Same tall antenna, but noncompliant at body (margin -10 dB) means iso
    // slant blows up to 49.9 * 10^0.5 ≈ 157.8 m; horizontal intersection at
    // observer height is sqrt(157.8² - 48.5²) ≈ 150.2 m.
    const result = computeComplianceFootprint(
      makeInputs({
        antennaRadiatorPos: [0, 50, 0],
        bodyCenterPos: [0, 1.1, 10],
        marginDb: -10,
      }),
    )
    expect(result.degenerate).toBe(false)
    expect(result.maxR).toBeGreaterThan(140)
    expect(result.maxR).toBeLessThan(170)
  })

  it('returns a degenerate footprint when iso-sphere is entirely above observer', () => {
    // Antenna 50 m up, compliance very compliant (margin_db = +30, iso-S_inc at small 3-D distance)
    // and body far away. Then d_iso_3d << dh, so no ring on the ground at 1.5 m.
    const result = computeComplianceFootprint(
      makeInputs({
        antennaRadiatorPos: [0, 50, 0],
        bodyCenterPos: [0, 1.1, 10],
        marginDb: 30,
      }),
    )
    expect(result.degenerate).toBe(true)
    expect(result.maxR).toBe(0)
  })
})

describe('computeComplianceFootprint — patch (directional)', () => {
  it('forward direction gets the correct radius and back direction shrinks', () => {
    // Patch boresight locked to (0, 0, -1). Body placed at +z behind the antenna
    // gets little power, but we pass the floor fraction so G_body is not 0.
    // Instead, place body at forward direction (-z) = boresight.
    const inputs = makeInputs({
      antennaRadiatorPos: [0, 2, 0],
      bodyCenterPos: [0, 1.1, -10], // -z = boresight of patch
      marginDb: 0,
      patternType: 'patch',
      elements: [ISO_ELEMENT],
    })
    const result = computeComplianceFootprint(inputs)
    expect(result.degenerate).toBe(false)
    expect(result.isCircular).toBe(false)

    // Forward azimuth is az = pi (since dir.set(sin(pi), 0, cos(pi)) = (0,0,-1)).
    // That maps to index i such that i / n * 2pi ≈ pi => i = n/2.
    const n = result.radii.length
    const idxForward = Math.round(n / 2)
    const idxBack = 0

    const rForward = result.radii[idxForward]
    const rBack = result.radii[idxBack]

    expect(rForward).toBeGreaterThan(rBack * 1.5) // forward ring much larger than back
    // Forward ring should be close to the body horizontal distance.
    expect(rForward).toBeGreaterThan(9)
    expect(rForward).toBeLessThan(12)
  })
})

describe('computeComplianceFootprint — robustness', () => {
  it('handles marginDb = NaN by returning a degenerate result', () => {
    const result = computeComplianceFootprint(makeInputs({ marginDb: NaN }))
    expect(result.degenerate).toBe(true)
    expect(result.maxR).toBe(0)
  })

  it('handles body at same position as antenna (d_body = 0)', () => {
    const result = computeComplianceFootprint(
      makeInputs({ bodyCenterPos: [0, 2, 0], antennaRadiatorPos: [0, 2, 0] }),
    )
    expect(result.degenerate).toBe(true)
  })

  it('respects maxRadiusM cap for highly noncompliant scenarios', () => {
    const result = computeComplianceFootprint(
      makeInputs({ marginDb: -80, maxRadiusM: 200 }),
    )
    for (let i = 0; i < result.radii.length; i++) {
      expect(result.radii[i]).toBeLessThanOrEqual(200.001)
    }
  })

  it('flags reference as invalid if body is in a deep pattern null', () => {
    // Patch boresight is (0, 0, -1). Body placed at +z (behind) hits the null.
    const result = computeComplianceFootprint(
      makeInputs({
        bodyCenterPos: [0, 1.1, 10],
        patternType: 'patch',
        elements: [ISO_ELEMENT],
      }),
    )
    expect(result.referenceValid).toBe(false)
  })
})

describe('smoothRadii', () => {
  it('is idempotent on a constant array', () => {
    const r = new Float32Array([5, 5, 5, 5, 5])
    const out = smoothRadii(r, 3)
    for (let i = 0; i < out.length; i++) expect(out[i]).toBe(5)
  })

  it('returns a copy — does not mutate input', () => {
    const r = new Float32Array([1, 2, 3, 2, 1])
    const originalFirst = r[0]
    smoothRadii(r, 1)
    expect(r[0]).toBe(originalFirst)
  })

  it('reduces variation with increasing passes', () => {
    const r = new Float32Array([10, 0, 10, 0, 10, 0, 10, 0])
    const smoothed = smoothRadii(r, 5)
    const range = (arr: Float32Array) => {
      let mn = Infinity, mx = -Infinity
      for (let i = 0; i < arr.length; i++) {
        if (arr[i] < mn) mn = arr[i]
        if (arr[i] > mx) mx = arr[i]
      }
      return mx - mn
    }
    expect(range(smoothed)).toBeLessThan(range(r))
  })
})

describe('DEFAULT_OBSERVER_HEIGHT_M', () => {
  it('is 1.5 m (standing adult chest)', () => {
    expect(DEFAULT_OBSERVER_HEIGHT_M).toBe(1.5)
  })
})

// Parametric sanity: the horizontal-plane body-direction sample must recover
// exactly the body horizontal distance at margin_db = 0 for isotropic.
describe('computeComplianceFootprint — parametric check against closed form', () => {
  it.each([
    { bodyZ: 5 },
    { bodyZ: 10 },
    { bodyZ: 25 },
  ])('at margin_db=0 the forward azimuth r matches body distance (z=$bodyZ)', ({ bodyZ }) => {
    const inputs = makeInputs({
      antennaRadiatorPos: [0, 2, 0],
      bodyCenterPos: [0, 1.5, -bodyZ], // body at +negZ = forward boresight-ish
      marginDb: 0,
      nAzimuth: 128,
      patternType: 'isotropic',
    })
    const result = computeComplianceFootprint(inputs)
    // Isotropic => all azimuths equal. Check max matches d_body_horiz corrected for dh.
    // d_body_3d = sqrt(bodyZ² + (2-1.5)²). For margin=0, iso-S is sphere radius d_body_3d;
    // horizontal intersection at observer height (dh = 0.5) is sqrt(d_body_3d² - 0.25).
    const dBody3d = Math.sqrt(bodyZ * bodyZ + 0.25)
    const expectedR = Math.sqrt(Math.max(dBody3d * dBody3d - 0.25, 0))
    expect(Math.abs(result.maxR - expectedR)).toBeLessThan(0.2)
  })
})

// ---------------------------------------------------------------------------
// 3-D iso-S_inc surface
// ---------------------------------------------------------------------------

function makeVolumeInputs(partial: Partial<VolumeInputs>): VolumeInputs {
  return {
    antennaRadiatorPos: [0, 2, 0],
    bodyCenterPos: [0, 1.1, 10],
    marginDb: 0,
    patternType: 'isotropic',
    elements: [ISO_ELEMENT],
    nAzimuth: 32,
    nElevation: 17,
    ...partial,
  }
}

describe('computeComplianceVolume — isotropic', () => {
  it('produces a sphere of radius ~d_body at margin_db = 0', () => {
    const result = computeComplianceVolume(makeVolumeInputs({ marginDb: 0 }))
    expect(result.degenerate).toBe(false)
    expect(result.referenceValid).toBe(true)
    const dBody3d = Math.sqrt(10 * 10 + 0.9 * 0.9)
    const { nAzimuth, nElevation } = result
    for (let i = 0; i < nAzimuth; i++) {
      for (let j = 0; j < nElevation; j++) {
        const r = result.radii[i * nElevation + j]
        expect(Math.abs(r - dBody3d)).toBeLessThan(0.1)
      }
    }
  })

  it('scales r by 10^(-margin/20)', () => {
    const r0 = computeComplianceVolume(makeVolumeInputs({ marginDb: 0 })).maxR
    const r6 = computeComplianceVolume(makeVolumeInputs({ marginDb: 6 })).maxR
    expect(r6 / r0).toBeCloseTo(Math.pow(10, -6 / 20), 2)
  })

  it('endpoints cover -pi/2 to +pi/2 exactly', () => {
    const v = computeComplianceVolume(makeVolumeInputs({ nElevation: 5 }))
    expect(v.elevationsRad[0]).toBeCloseTo(-Math.PI / 2, 5)
    expect(v.elevationsRad[v.nElevation - 1]).toBeCloseTo(Math.PI / 2, 5)
  })
})

describe('computeComplianceVolume — directional pattern', () => {
  it('lobes towards the patch boresight and shrinks behind', () => {
    const inputs = makeVolumeInputs({
      antennaRadiatorPos: [0, 2, 0],
      bodyCenterPos: [0, 1.1, -10], // forward boresight of patch
      marginDb: 0,
      patternType: 'patch',
      elements: [ISO_ELEMENT],
      nAzimuth: 64,
      nElevation: 17,
    })
    const result = computeComplianceVolume(inputs)
    expect(result.degenerate).toBe(false)

    // Find the horizontal slice (elevation ≈ 0). For odd nElevation=17, j=8 is el=0.
    const jEq = Math.floor((result.nElevation - 1) / 2)
    // Forward azimuth (dir = (0, 0, -1)) maps to az = atan2(0, -1) = pi,
    // i.e. i ≈ nAzimuth / 2.
    const iForward = Math.round(result.nAzimuth / 2)
    const iBack = 0

    const rForward = result.radii[iForward * result.nElevation + jEq]
    const rBack = result.radii[iBack * result.nElevation + jEq]
    expect(rForward).toBeGreaterThan(rBack * 1.5)
    // The forward sample is the body direction itself — at margin=0 it equals d_body.
    const dBody3d = Math.sqrt(10 * 10 + 0.9 * 0.9)
    expect(Math.abs(rForward - dBody3d)).toBeLessThan(0.5)
  })

  it('short_dipole has a null along its axis', () => {
    // Dipole along y-axis. Gain ∝ sin²(angle from y-axis), so along ±y the gain is 0.
    const result = computeComplianceVolume(makeVolumeInputs({
      bodyCenterPos: [0, 1.1, 10],
      patternType: 'short_dipole',
    }))
    // Zenith sample (elevation = +pi/2) points along +y; gain = 0 => radius floor.
    const jZenith = result.nElevation - 1
    for (let i = 0; i < result.nAzimuth; i++) {
      expect(result.radii[i * result.nElevation + jZenith]).toBeLessThan(0.5)
    }
  })
})

describe('computeComplianceVolume — robustness', () => {
  it('returns degenerate for NaN margin', () => {
    const result = computeComplianceVolume(makeVolumeInputs({ marginDb: NaN }))
    expect(result.degenerate).toBe(true)
    expect(result.maxR).toBe(0)
  })

  it('returns degenerate when antenna and body coincide', () => {
    const result = computeComplianceVolume(makeVolumeInputs({
      antennaRadiatorPos: [0, 2, 0],
      bodyCenterPos: [0, 2, 0],
    }))
    expect(result.degenerate).toBe(true)
  })

  it('caps every sample at maxRadiusM for highly noncompliant inputs', () => {
    const result = computeComplianceVolume(makeVolumeInputs({
      marginDb: -80,
      maxRadiusM: 120,
    }))
    for (let k = 0; k < result.radii.length; k++) {
      expect(result.radii[k]).toBeLessThanOrEqual(120.001)
    }
  })

  it('flags reference as invalid when body is in a pattern null', () => {
    const result = computeComplianceVolume(makeVolumeInputs({
      bodyCenterPos: [0, 1.1, 10], // back of patch
      patternType: 'patch',
    }))
    expect(result.referenceValid).toBe(false)
  })

  it('clamps nAzimuth and nElevation to sensible minima', () => {
    const result = computeComplianceVolume(makeVolumeInputs({
      nAzimuth: 2, // will be clamped to 4
      nElevation: 1, // will be clamped to 3
    }))
    expect(result.nAzimuth).toBe(4)
    expect(result.nElevation).toBe(3)
  })
})
