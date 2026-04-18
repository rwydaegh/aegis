import { useSimulationStore } from '@/stores/simulation'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { useUIStore } from '@/stores/ui'
import { useMIMOStore } from '@/stores/mimo'
import type { QuantityKey } from '@/api/types'
import Tex from '@/components/ui/Tex'
import { cn } from '@/lib/utils'
import { AlertTriangle, RefreshCw } from 'lucide-react'

function tightestMarginDb(checks: Array<{ margin_db?: number | null }>): number | null {
  const margins = checks
    .map(c => c.margin_db)
    .filter((m): m is number => m != null && isFinite(m))
  if (margins.length === 0) return null
  return Math.min(...margins)
}

function computeMaxPowerDbm(checks: Array<{ margin_db?: number | null }>, currentPowerDbm: number): number | null {
  const minMarginDb = tightestMarginDb(checks)
  if (minMarginDb == null) return null
  return currentPowerDbm + minMarginDb
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

interface CheckEntry {
  label: string
  value: number
  limit: number
  unit: string
  pass: boolean
  ratio: number
  margin_db?: number | null
}

function statusColor(check: Pick<CheckEntry, 'pass' | 'ratio'>): string {
  if (!check.pass) return '#f87171'
  if (check.ratio > 0.8) return '#fbbf24'
  return '#4ade80'
}

function statusLabel(check: Pick<CheckEntry, 'pass' | 'ratio'>): string {
  if (!check.pass) return 'FAIL'
  if (check.ratio > 0.8) return 'WARN'
  return 'PASS'
}

function statusTextClass(check: Pick<CheckEntry, 'pass' | 'ratio'>): string {
  if (!check.pass) return 'text-destructive'
  if (check.ratio > 0.8) return 'text-amber-400'
  return 'text-success'
}

function CheckRow({ check }: { check: CheckEntry }) {
  const color = statusColor(check)
  const tex = LABEL_TEX[check.label]
  return (
    <div className="mb-1.5">
      <div className="flex justify-between text-foreground/90 gap-2 items-baseline">
        <span className="flex-1">{tex ? <Tex math={tex} /> : check.label}</span>
        <span className="whitespace-nowrap">
          {check.value.toFixed(2)} / {check.limit.toFixed(2)} {check.unit}
        </span>
        {check.margin_db != null && (
          <span className={cn('min-w-[42px] text-right tabular-nums', statusTextClass(check))}>
            {check.margin_db > 0 ? '+' : ''}{check.margin_db.toFixed(1)}dB
          </span>
        )}
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
}

interface ComplianceSummaryProps {
  allChecks: CheckEntry[]
  powerDbm: number
  onSetPower: (v: number) => void
  freqHz: number
}

function ComplianceSummary({ allChecks, powerDbm, onSetPower, freqHz }: ComplianceSummaryProps) {
  const maxPowerDbm = computeMaxPowerDbm(allChecks, powerDbm)
  const visibleMarginDb = tightestMarginDb(allChecks)
  if (visibleMarginDb == null) return null
  return (
    <div className="border-t border-border pt-2 mt-2 text-muted-foreground">
      <div className="flex justify-between">
        <span>Margin</span>
        <span className={visibleMarginDb >= 0 ? 'text-success' : 'text-destructive'}>
          {visibleMarginDb > 0 ? '+' : ''}{visibleMarginDb.toFixed(1)} dB
        </span>
      </div>
      {maxPowerDbm != null && (() => {
        const safeMaxPowerDbm = Math.floor(maxPowerDbm * 10) / 10
        return (
          <div
            className="flex justify-between cursor-pointer hover:text-blue-200 transition-colors"
            title="Click to set TX power to max compliant value"
            onClick={() => onSetPower(safeMaxPowerDbm)}
          >
            <span>Max TX power</span>
            <span className="text-blue-300">{safeMaxPowerDbm.toFixed(1)} dBm</span>
          </div>
        )
      })()}
      <div className="flex justify-between">
        <span>Frequency</span>
        <span>{(freqHz / 1e9).toFixed(1)} GHz</span>
      </div>
    </div>
  )
}

const PANEL_BASE = 'bg-card/80 backdrop-blur-md rounded-lg border border-border p-3 font-mono text-xs min-w-[280px]'

function ComplianceHeader({ scenario }: { scenario: string }) {
  return (
    <div className="flex justify-between mb-2">
      <span className="text-muted-foreground text-[10px] tracking-widest">
        COMPLIANCE (ICNIRP 2020)
      </span>
      <span className="text-blue-300 text-[10px]">
        {scenario === 'general_public' ? 'General Public' : 'Occupational'}
      </span>
    </div>
  )
}

export default function CompliancePanel() {
  const { stats } = useActiveSimulation()
  const enabledQuantities = useSimulationStore(s => s.enabledQuantities)
  const powerDbm = useSimulationStore(s => s.powerDbm)
  const setPowerDbm = useSimulationStore(s => s.setPowerDbm)
  const scenario = useUIStore(s => s.exposureScenario)
  const isComputing = useUIStore(s => s.isComputing)
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const mimoError = useMIMOStore(s => s.lastComputeError)
  const mimoRetry = useMIMOStore(s => s.retryCompute)

  if (mimoEnabled && mimoError && !stats) {
    return (
      <div className={PANEL_BASE}>
        <ComplianceHeader scenario={scenario} />
        <div className="flex items-start gap-1.5 px-1.5 py-1.5 rounded bg-destructive/10 border border-destructive/30 text-destructive">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-[11px] leading-tight font-semibold">Compliance unavailable</div>
            <div className="text-[10px] leading-tight opacity-80 mt-0.5">
              Last MIMO compute failed: {mimoError}. Re-run to refresh.
            </div>
          </div>
          <button
            onClick={mimoRetry}
            disabled={isComputing}
            className={cn(
              'flex items-center gap-0.5 text-[10px] px-1.5 py-0.5 rounded border border-destructive/40',
              'hover:bg-destructive/20 transition-colors',
              isComputing && 'opacity-40 cursor-not-allowed',
            )}
            title="Retry MIMO compute"
          >
            <RefreshCw className="w-3 h-3" />
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!stats) return null

  if (!stats.compliance) {
    if (stats.warning) {
      return (
        <div className={PANEL_BASE}>
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

  const visibleChecks = compliance.checks.filter((check: CheckEntry) => {
    if (!check.pass) return true
    const key = LABEL_TO_KEY[check.label]
    return key ? enabledQuantities.has(key) : true
  })

  const emptyMessage = compliance.checks.length > 0 && compliance.freq_hz < 6e9
    ? 'S_ab limits do not apply below 6 GHz. Enable SAR_wb for compliance.'
    : 'Enable quantities to see compliance checks'

  return (
    <div className={cn(PANEL_BASE, isComputing && 'shimmer-panel')} data-testid="compliance-panel">
      <ComplianceHeader scenario={scenario} />

      {visibleChecks.length === 0 ? (
        <div className="text-muted-foreground/60 text-[11px] italic">{emptyMessage}</div>
      ) : (
        <>
          {visibleChecks.map((check: CheckEntry, i: number) => (
            <CheckRow key={i} check={check} />
          ))}
          <ComplianceSummary
            allChecks={compliance.checks}
            powerDbm={powerDbm}
            onSetPower={setPowerDbm}
            freqHz={compliance.freq_hz}
          />
        </>
      )}
    </div>
  )
}
