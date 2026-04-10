import { useSimulationStore } from '@/stores/simulation'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { useUIStore } from '@/stores/ui'
import type { QuantityKey } from '@/api/types'
import Tex from '@/components/ui/Tex'
import { cn } from '@/lib/utils'

function computeMaxPowerDbm(checks: Array<{ ratio: number }>, currentPowerDbm: number): number | null {
  if (checks.length === 0) return null
  const maxRatio = Math.max(...checks.map(c => c.ratio))
  if (maxRatio <= 0) return null
  // P_max = P_ref / maxRatio (linear), convert to dB offset
  return currentPowerDbm - 10 * Math.log10(maxRatio)
}

const LABEL_TEX: Record<string, string> = {
  'S_ab (4 cm^2)': 'S_\\text{ab}\\;(4\\,\\text{cm}^2)',
  'S_ab (1 cm^2)': 'S_\\text{ab}\\;(1\\,\\text{cm}^2)',
  'SAR_wb': '\\text{SAR}_\\text{wb}',
  'S_inc (local)': 'S_\\text{inc}\\;(\\text{local})',
  'S_inc (whole-body)': 'S_\\text{inc}\\;(\\text{wb})',
}

const LABEL_TO_KEY: Record<string, QuantityKey> = {
  'S_ab (4 cm^2)': 'sab_4cm2',
  'S_ab (1 cm^2)': 'sab_1cm2',
  'SAR_wb': 'sar_wb',
  'S_inc (local)': 'sinc_local',
  'S_inc (whole-body)': 'sinc_wb',
}

function statusColor(check: { pass: boolean; ratio: number }): string {
  if (!check.pass) return '#f87171'
  if (check.ratio > 0.8) return '#fbbf24'
  return '#4ade80'
}

function statusLabel(check: { pass: boolean; ratio: number }): string {
  if (!check.pass) return 'FAIL'
  if (check.ratio > 0.8) return 'WARN'
  return 'PASS'
}

function statusTextClass(check: { pass: boolean; ratio: number }): string {
  if (!check.pass) return 'text-destructive'
  if (check.ratio > 0.8) return 'text-amber-400'
  return 'text-success'
}

export default function CompliancePanel() {
  const { stats } = useActiveSimulation()
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)
  const powerDbm = useSimulationStore(s => s.powerDbm)
  const setPowerDbm = useSimulationStore(s => s.setPowerDbm)
  const scenario = useUIStore(s => s.exposureScenario)
  const isComputing = useUIStore(s => s.isComputing)
  if (!stats) return null
  if (!stats.compliance) {
    if (stats.warning) {
      return (
        <div className="bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 font-mono text-xs min-w-[280px]">
          <div className="mb-2">
            <span className="text-muted-foreground text-[10px] tracking-widest">
              COMPLIANCE (ICNIRP 2020)
            </span>
          </div>
          <div className="text-amber-400 text-[11px]">
            Compliance check not available below 6 GHz.
          </div>
          <div className="text-muted-foreground text-[11px] mt-1">
            ICNIRP 2020 absorbed power density limits apply from 6 to 300 GHz.
            SAR-based limits for lower frequencies are not yet implemented.
          </div>
        </div>
      )
    }
    return null
  }
  const { compliance } = stats

  const visibleChecks = compliance.checks.filter(check => {
    if (!check.pass) return true // Always show failing checks
    const key = LABEL_TO_KEY[check.label]
    return key ? enabledQuantities.has(key) : true
  })

  return (
    <div className={cn(
      'bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 font-mono text-xs min-w-[280px]',
      isComputing && 'shimmer-panel',
    )}>
      <div className="flex justify-between mb-2">
        <span className="text-muted-foreground text-[10px] tracking-widest">
          COMPLIANCE (ICNIRP 2020)
        </span>
        <span className="text-blue-300 text-[10px]">
          {scenario === 'general_public' ? 'General Public' : 'Occupational'}
        </span>
      </div>

      {visibleChecks.length === 0 ? (
        <div className="text-muted-foreground/60 text-[11px] italic">
          {compliance.checks.length > 0 && compliance.freq_hz < 6e9
            ? 'S_ab limits do not apply below 6 GHz. Enable SAR_wb for compliance.'
            : 'Enable quantities to see compliance checks'}
        </div>
      ) : visibleChecks.map((check, i) => {
        const color = statusColor(check)
        const tex = LABEL_TEX[check.label]
        return (
          <div key={i} className="mb-1.5">
            <div className="flex justify-between text-foreground/90 gap-2 items-baseline">
              <span className="flex-1">{tex ? <Tex math={tex} /> : check.label}</span>
              <span className="whitespace-nowrap">{check.value.toFixed(2)} / {check.limit.toFixed(2)} {check.unit}</span>
              <span className={cn('font-bold min-w-[35px] text-right', statusTextClass(check))}>
                {statusLabel(check)}
              </span>
            </div>
            <div className="bg-muted h-[3px] rounded-sm mt-0.5">
              <div
                className="h-full rounded-sm"
                style={{
                  backgroundColor: color,
                  width: `${Math.min(check.ratio * 100, 100)}%`,
                }}
              />
            </div>
          </div>
        )
      })}

      {visibleChecks.length > 0 && (() => {
        // Use ALL checks for overall compliance determination, not just visible ones
        const allChecks = compliance.checks
        const maxPowerDbm = computeMaxPowerDbm(allChecks, powerDbm)
        const visibleMarginDb = Math.min(...allChecks.map(c => c.ratio > 0 ? 10 * Math.log10(1 / c.ratio) : Infinity))
        if (!isFinite(visibleMarginDb)) return null
        return (
          <div className="border-t border-border pt-2 mt-2 text-muted-foreground">
            <div className="flex justify-between">
              <span>Margin</span>
              <span className={visibleMarginDb >= 0 ? 'text-success' : 'text-destructive'}>
                {visibleMarginDb > 0 ? '+' : ''}{visibleMarginDb.toFixed(1)} dB
              </span>
            </div>
            {maxPowerDbm != null && (
              <div
                className="flex justify-between cursor-pointer hover:text-blue-200 transition-colors"
                title="Click to set TX power to max compliant value"
                onClick={() => setPowerDbm(parseFloat(maxPowerDbm.toFixed(1)))}
              >
                <span>Max TX power</span>
                <span className="text-blue-300">{maxPowerDbm.toFixed(1)} dBm</span>
              </div>
            )}
            <div className="flex justify-between">
              <span>Frequency</span>
              <span>{(compliance.freq_hz / 1e9).toFixed(1)} GHz</span>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
