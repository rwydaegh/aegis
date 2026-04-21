import { describe, it, expect } from 'vitest'
import { computeFidelityTier, computeUpgradePath } from '../fidelityTier'

const confident = 'gov:brussels'
const estimated = 'est:tech+band'

function baseConfidentProv(overrides: Record<string, string> = {}): Record<string, string> {
  return {
    Power: confident,
    Frequency: confident,
    Azimuth: confident,
    CenterHeight: confident,
    Gain: confident,
    Electrical_Tilt: confident,
    Mechanical_Tilt: confident,
    Horizontal_Beamwidth: confident,
    Vertical_Beamwidth: confident,
    Pattern: 'measured:vendor_xyz',
    ...overrides,
  }
}

describe('computeFidelityTier', () => {
  it('returns location_only for null provenance', () => {
    expect(computeFidelityTier(null)).toBe('location_only')
  })

  it('returns full when all fields are confident and pattern is real', () => {
    expect(computeFidelityTier(baseConfidentProv())).toBe('full')
  })

  it('returns spatial when pattern is synthetic but other fields are confident/available', () => {
    expect(computeFidelityTier(baseConfidentProv({ Pattern: 'synthetic:gaussian' }))).toBe('spatial')
  })

  it('returns spatial when tilts and beamwidths are estimated (est is acceptable)', () => {
    const prov = baseConfidentProv({
      Electrical_Tilt: estimated,
      Mechanical_Tilt: estimated,
      Horizontal_Beamwidth: estimated,
      Vertical_Beamwidth: estimated,
      Pattern: 'synthetic:gaussian',
    })
    expect(computeFidelityTier(prov)).toBe('spatial')
  })

  it('drops to geometric when gain is estimated (spatial requires confident gain)', () => {
    expect(computeFidelityTier(baseConfidentProv({ Gain: estimated }))).toBe('geometric')
  })

  it('drops to bound when power is estimated (geometric requires confident power)', () => {
    expect(computeFidelityTier(baseConfidentProv({ Power: estimated }))).toBe('bound')
  })

  it('returns bound when only power and frequency are available', () => {
    const prov: Record<string, string> = {
      Power: estimated,
      Frequency: confident,
      Azimuth: 'missing',
      CenterHeight: 'missing',
      Gain: 'missing',
      Electrical_Tilt: 'missing',
      Mechanical_Tilt: 'missing',
      Horizontal_Beamwidth: 'missing',
      Vertical_Beamwidth: 'missing',
      Pattern: '',
    }
    expect(computeFidelityTier(prov)).toBe('bound')
  })

  it('returns location_only when power is missing', () => {
    const prov: Record<string, string> = {
      Power: 'missing',
      Frequency: confident,
      Azimuth: confident,
      CenterHeight: confident,
      Gain: confident,
      Electrical_Tilt: 'missing',
      Mechanical_Tilt: 'missing',
      Horizontal_Beamwidth: 'missing',
      Vertical_Beamwidth: 'missing',
      Pattern: '',
    }
    expect(computeFidelityTier(prov)).toBe('location_only')
  })
})

describe('computeUpgradePath', () => {
  it('reports all fields missing for null provenance', () => {
    expect(computeUpgradePath(null)).toEqual(['All RF parameters missing'])
  })

  it('returns no issues for a fully confident antenna with real pattern', () => {
    expect(computeUpgradePath(baseConfidentProv())).toEqual([])
  })

  it('flags only the missing pattern when everything else is confident', () => {
    expect(computeUpgradePath(baseConfidentProv({ Pattern: 'synthetic:gaussian' }))).toEqual([
      'Need real antenna pattern file',
    ])
  })

  it('does not flag estimated tilt or beamwidth (they do not block any tier)', () => {
    const prov = baseConfidentProv({
      Electrical_Tilt: estimated,
      Mechanical_Tilt: estimated,
      Horizontal_Beamwidth: estimated,
      Vertical_Beamwidth: estimated,
    })
    expect(computeUpgradePath(prov)).toEqual([])
  })

  it('flags estimated power because it blocks geometric/spatial/full', () => {
    const prov = baseConfidentProv({ Power: estimated })
    expect(computeUpgradePath(prov)).toContain('EIRP is estimated')
  })

  it('flags estimated gain because it blocks spatial/full', () => {
    const prov = baseConfidentProv({ Gain: estimated })
    expect(computeUpgradePath(prov)).toContain('Gain is estimated')
  })

  it('flags missing tilt but not estimated tilt', () => {
    const prov = baseConfidentProv({
      Electrical_Tilt: 'missing',
      Mechanical_Tilt: 'missing',
      Pattern: 'synthetic:gaussian',
    })
    const issues = computeUpgradePath(prov)
    expect(issues).toContain('Need electrical tilt')
    expect(issues).toContain('Need mechanical tilt')
    expect(issues).toContain('Need real antenna pattern file')
  })

  it('reports all missing core fields for a sparse provenance', () => {
    const prov: Record<string, string> = {
      Power: 'missing',
      Frequency: 'missing',
      Azimuth: 'missing',
      CenterHeight: 'missing',
      Gain: 'missing',
      Electrical_Tilt: 'missing',
      Mechanical_Tilt: 'missing',
      Horizontal_Beamwidth: 'missing',
      Vertical_Beamwidth: 'missing',
      Pattern: '',
    }
    const issues = computeUpgradePath(prov)
    expect(issues).toContain('Need Power (EIRP)')
    expect(issues).toContain('Need Frequency')
    expect(issues).toContain('Need Azimuth')
    expect(issues).toContain('Need antenna height')
    expect(issues).toContain('Need antenna gain')
    expect(issues).toContain('Need real antenna pattern file')
  })
})
