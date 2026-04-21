import { describe, it, expect } from 'vitest'
import { computeMaxPowerDbm, tightestMarginDb, WARN_HEADROOM_DB } from '../CompliancePanel'

describe('tightestMarginDb', () => {
  it('returns the minimum finite margin', () => {
    const checks = [
      { margin_db: 34.1 },
      { margin_db: 33.2 },
      { margin_db: 37.0 },
    ]
    expect(tightestMarginDb(checks)).toBeCloseTo(33.2, 5)
  })

  it('ignores null and non-finite margins', () => {
    const checks = [
      { margin_db: null },
      { margin_db: Infinity },
      { margin_db: 12.5 },
    ]
    expect(tightestMarginDb(checks)).toBeCloseTo(12.5, 5)
  })

  it('returns null for empty or all-null checks', () => {
    expect(tightestMarginDb([])).toBeNull()
    expect(tightestMarginDb([{ margin_db: null }, { margin_db: null }])).toBeNull()
  })
})

describe('computeMaxPowerDbm', () => {
  // Repro of issue #726: at 28 GHz with the deployed URL args, the tightest
  // margin is S_inc (local) ≈ 33.17 dB. Setting TX to (43 + 33.17) dBm puts
  // that check at ratio=1.0, which passes ICNIRP but trips the ratio>0.8 WARN.
  // The advertised max must sit at least WARN_HEADROOM_DB below the ceiling so
  // clicking it lands in PASS.
  it('stays at least WARN_HEADROOM_DB below the tightest-check ceiling', () => {
    const checks = [
      { margin_db: 34.09 },  // S_ab (4 cm^2)
      { margin_db: 33.17 },  // S_inc (local) - tightest
      { margin_db: 36.99 },  // S_inc (whole-body)
    ]
    const max = computeMaxPowerDbm(checks, 43.0)
    expect(max).not.toBeNull()
    // Ceiling is 43 + 33.17 = 76.17 dBm; advertised max must sit below it.
    expect(max!).toBeLessThanOrEqual(76.17 - WARN_HEADROOM_DB + 1e-9)
  })

  it('keeps every check in PASS (ratio <= 0.8) when TX is set to the advertised max', () => {
    // ratio(P) = 10^((P - P_ref - margin_ref) / 10); we need ratio <= 0.8 on the
    // tightest check after clicking. 0.8 corresponds to -log10(0.8)*10 ≈ 0.969 dB
    // of headroom, so WARN_HEADROOM_DB >= 0.97 guarantees PASS.
    const tightest = 33.17
    const checks = [{ margin_db: tightest }]
    const max = computeMaxPowerDbm(checks, 43.0)!
    const marginAtClick = tightest - (max - 43.0)
    const ratioAtClick = Math.pow(10, -marginAtClick / 10)
    expect(ratioAtClick).toBeLessThanOrEqual(0.8)
  })

  it('returns null when no check has a finite margin', () => {
    expect(computeMaxPowerDbm([], 43.0)).toBeNull()
    expect(computeMaxPowerDbm([{ margin_db: null }], 43.0)).toBeNull()
  })

  it('tracks current power linearly', () => {
    const checks = [{ margin_db: 10.0 }]
    const a = computeMaxPowerDbm(checks, 20.0)!
    const b = computeMaxPowerDbm(checks, 30.0)!
    expect(b - a).toBeCloseTo(10.0, 9)
  })
})
