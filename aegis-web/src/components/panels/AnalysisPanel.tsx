import { useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  Area,
} from 'recharts'
import { useSimulationStore } from '@/stores/simulation'
import { useUIStore } from '@/stores/ui'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import {
  fetchPowerSweep,
  fetchFrequencySweep,
  fetchLinkBudget,
} from '@/api/client'
import type {
  PowerSweepResult,
  FrequencySweepResult,
  LinkBudgetResult,
} from '@/api/client'
import Tex from '@/components/ui/Tex'

const labelClass = 'text-xs text-muted-foreground block mt-3 mb-1'
const inputClass =
  'w-full bg-background border border-border rounded px-2 py-1.5 text-sm text-foreground'
const btnClass =
  'text-xs px-3 py-1.5 rounded border border-border transition-colors cursor-pointer hover:bg-muted'
const btnPrimaryClass =
  'text-xs px-3 py-1.5 rounded border border-primary/40 bg-primary/15 text-primary transition-colors cursor-pointer hover:bg-primary/25'

// ---------------------------------------------------------------------------
// Collapsible section
// ---------------------------------------------------------------------------

function Section({
  title,
  open,
  onToggle,
  children,
}: {
  title: string
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border-b border-border/50 pb-2 mb-2 last:border-b-0">
      <button
        onClick={onToggle}
        className="flex items-center justify-between w-full text-xs font-medium py-1 cursor-pointer text-foreground"
      >
        <span>{title}</span>
        <span className="text-muted-foreground">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="mt-1">{children}</div>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Margin chart (shared between power sweep and frequency sweep)
// ---------------------------------------------------------------------------

function MarginChart({
  data,
  xLabel,
  xUnit,
  currentX,
  maxCompliantX,
}: {
  data: { x: number; margin: number; compliant: boolean }[]
  xLabel: string
  xUnit: string
  currentX?: number
  maxCompliantX?: number | null
}) {
  if (data.length === 0) return null

  const minMargin = Math.min(...data.map((d) => d.margin))
  const maxMargin = Math.max(...data.map((d) => d.margin))
  const yMin = Math.min(minMargin, -5)
  const yMax = Math.max(maxMargin, 5)

  return (
    <div className="mt-2">
      <ResponsiveContainer width="100%" height={140}>
        <LineChart
          data={data}
          margin={{ top: 4, right: 8, bottom: 16, left: 0 }}
        >
          <defs>
            <linearGradient id="marginFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4ade80" stopOpacity={0.15} />
              <stop offset="100%" stopColor="#4ade80" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="x"
            type="number"
            domain={['dataMin', 'dataMax']}
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v) => v.toFixed(0)}
            label={{
              value: `${xLabel} (${xUnit})`,
              position: 'bottom',
              fontSize: 9,
              fill: '#666',
              offset: 0,
            }}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 9, fill: '#888' }}
            tickFormatter={(v: number) => `${v > 0 ? '+' : ''}${v.toFixed(0)}`}
            width={35}
            label={{
              value: 'dB',
              angle: -90,
              position: 'insideLeft',
              fontSize: 9,
              fill: '#666',
              offset: 10,
            }}
          />
          <Tooltip
            contentStyle={{
              background: 'rgba(0,0,0,0.85)',
              border: '1px solid #333',
              borderRadius: 4,
              fontSize: 11,
            }}
            formatter={(value) => {
              const v = Number(value)
              return [`${v > 0 ? '+' : ''}${v.toFixed(1)} dB`, 'Margin']
            }}
            labelFormatter={(label) => {
              const v = Number(label)
              return `${xLabel}: ${v.toFixed(1)} ${xUnit}`
            }}
          />
          <ReferenceLine y={0} stroke="#f87171" strokeDasharray="4 2" strokeWidth={1.5} />
          {currentX != null && (
            <ReferenceLine
              x={currentX}
              stroke="#93c5fd"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{
                value: 'current',
                position: 'top',
                fontSize: 8,
                fill: '#93c5fd',
              }}
            />
          )}
          {maxCompliantX != null && (
            <ReferenceLine
              x={maxCompliantX}
              stroke="#fbbf24"
              strokeDasharray="3 3"
              strokeWidth={1}
              label={{
                value: 'max',
                position: 'top',
                fontSize: 8,
                fill: '#fbbf24',
              }}
            />
          )}
          <Area
            type="monotone"
            dataKey="margin"
            fill="url(#marginFill)"
            stroke="none"
            baseLine={0}
          />
          <Line
            type="monotone"
            dataKey="margin"
            stroke="#4ade80"
            strokeWidth={1.5}
            dot={false}
            activeDot={{ r: 3, fill: '#4ade80' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Power sweep section
// ---------------------------------------------------------------------------

/** Extract a compliance check value by label from stats. */
function checkValue(stats: { compliance?: { checks: Array<{ label: string; value: number }> } } | null, label: string): number | undefined {
  return stats?.compliance?.checks.find(c => c.label === label)?.value
}

function PowerSweepSection() {
  const { stats } = useActiveSimulation()
  const powerDbm = useSimulationStore((s) => s.powerDbm)
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const scenario = useUIStore((s) => s.exposureScenario)
  const setPowerDbm = useSimulationStore((s) => s.setPowerDbm)

  const [result, setResult] = useState<PowerSweepResult | null>(null)
  const [loading, setLoading] = useState(false)

  const peakSab = stats?.peak_sab_averaged ?? stats?.peak_sab
  const sincLocal = stats?.peaks?.sinc_local
  const sab1cm2 = stats?.peaks?.sab_1cm2
  const sarWb = checkValue(stats, 'SAR_wb')
  const sincWb = checkValue(stats, 'S_inc (whole-body)')

  const canSweep = peakSab != null && peakSab > 0

  async function runSweep() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchPowerSweep({
        sab_4cm2: peakSab!,
        freq_hz: freqGhz * 1e9,
        ref_power_dbm: powerDbm,
        scenario,
        sinc_local: sincLocal,
        sab_1cm2: sab1cm2,
        sar_wb: sarWb,
        sinc_wb: sincWb,
      })
      setResult(data)
    } catch {
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result
    ? result.power_dbm.map((p, i) => ({
        x: p,
        margin: result.margin_db[i],
        compliant: result.compliant[i],
      }))
    : []

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Find the maximum TX power that keeps all ICNIRP checks compliant.
      </p>
      <button
        onClick={runSweep}
        disabled={!canSweep || loading}
        className={canSweep && !loading ? btnPrimaryClass : `${btnClass} opacity-50 cursor-not-allowed`}
      >
        {loading ? 'Sweeping...' : 'Sweep power'}
      </button>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50 ml-2">
          Run a compute first
        </span>
      )}

      {result && (
        <>
          <MarginChart
            data={chartData}

            xLabel="TX Power"
            xUnit="dBm"
            currentX={powerDbm}
            maxCompliantX={result.p_max_compliant_dbm}
          />
          {result.p_max_compliant_dbm != null && (
            <div className="flex items-center justify-between mt-2 text-xs">
              <span className="text-muted-foreground">
                Max compliant: <span className="text-foreground font-medium">{result.p_max_compliant_dbm.toFixed(1)} dBm</span>
              </span>
              <button
                onClick={() =>
                  setPowerDbm(
                    Math.floor(result.p_max_compliant_dbm! * 10) / 10,
                  )
                }
                className={btnClass}
              >
                Set
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Frequency sweep section
// ---------------------------------------------------------------------------

function FrequencySweepSection() {
  const { stats } = useActiveSimulation()
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const scenario = useUIStore((s) => s.exposureScenario)

  const [result, setResult] = useState<FrequencySweepResult | null>(null)
  const [loading, setLoading] = useState(false)

  const peakSab = stats?.peak_sab_averaged ?? stats?.peak_sab
  const sincLocal = stats?.peaks?.sinc_local
  const sab1cm2 = stats?.peaks?.sab_1cm2
  const sarWb = checkValue(stats, 'SAR_wb')
  const sincWb = checkValue(stats, 'S_inc (whole-body)')

  const canSweep = peakSab != null && peakSab > 0

  async function runSweep() {
    if (!canSweep) return
    setLoading(true)
    try {
      const data = await fetchFrequencySweep({
        sab_4cm2: peakSab!,
        scenario,
        sinc_local: sincLocal,
        sab_1cm2: sab1cm2,
        sar_wb: sarWb,
        sinc_wb: sincWb,
      })
      setResult(data)
    } catch {
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = result
    ? result.freq_ghz.map((f, i) => ({
        x: f,
        margin: result.margin_db[i],
        compliant: result.compliant[i],
      }))
    : []

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        See how compliance margin changes across the frequency spectrum at
        current exposure level.
      </p>
      <button
        onClick={runSweep}
        disabled={!canSweep || loading}
        className={canSweep && !loading ? btnPrimaryClass : `${btnClass} opacity-50 cursor-not-allowed`}
      >
        {loading ? 'Sweeping...' : 'Sweep frequencies'}
      </button>
      {!canSweep && (
        <span className="text-[10px] text-muted-foreground/50 ml-2">
          Run a compute first
        </span>
      )}

      {result && (
        <MarginChart
          data={chartData}

          xLabel="Frequency"
          xUnit="GHz"
          currentX={freqGhz}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Link budget section
// ---------------------------------------------------------------------------

function LinkBudgetSection() {
  const powerDbm = useSimulationStore((s) => s.powerDbm)
  const freqGhz = useSimulationStore((s) => s.freqGhz)
  const scenario = useUIStore((s) => s.exposureScenario)

  const [gainDbi, setGainDbi] = useState(15)
  const [distanceM, setDistanceM] = useState(5)
  const [result, setResult] = useState<LinkBudgetResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function calculate() {
    setLoading(true)
    try {
      const data = await fetchLinkBudget({
        tx_power_dbm: powerDbm,
        antenna_gain_dbi: gainDbi,
        distance_m: distanceM,
        freq_hz: freqGhz * 1e9,
        scenario,
      })
      setResult(data)
    } catch {
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Quick compliance estimate from TX power, gain, and distance (free-space
        path loss, normal incidence).
      </p>

      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className={labelClass}>Antenna gain (dBi)</label>
          <input
            type="number"
            value={gainDbi}
            onChange={(e) => setGainDbi(Number(e.target.value))}
            className={inputClass}
            step={1}
          />
        </div>
        <div>
          <label className={labelClass}>Distance (m)</label>
          <input
            type="number"
            value={distanceM}
            onChange={(e) => setDistanceM(Number(e.target.value))}
            className={inputClass}
            step={0.5}
            min={0.1}
          />
        </div>
      </div>

      <div className="flex items-center gap-2 mt-3">
        <button
          onClick={calculate}
          disabled={loading || distanceM <= 0}
          className={!loading && distanceM > 0 ? btnPrimaryClass : `${btnClass} opacity-50 cursor-not-allowed`}
        >
          {loading ? 'Calculating...' : 'Calculate'}
        </button>
        <span className="text-[10px] text-muted-foreground/50">
          {powerDbm.toFixed(1)} dBm @ {freqGhz.toFixed(1)} GHz
        </span>
      </div>

      {result && (
        <div className="mt-3 space-y-1.5 text-xs">
          <div className="flex justify-between">
            <span className="text-muted-foreground">
              <Tex math="S_\text{inc}" />
            </span>
            <span>{result.sinc.toFixed(2)} W/m²</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">
              <Tex math="S_\text{ab}" /> (estimate)
            </span>
            <span>{result.sab_estimate.toFixed(2)} W/m²</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">
              <Tex math="T_0" />
            </span>
            <span>{result.T0.toFixed(3)}</span>
          </div>
          <div className="flex justify-between border-t border-border/50 pt-1.5">
            <span className="text-muted-foreground">Status</span>
            <span
              className={`font-medium ${result.compliant ? 'text-green-400' : 'text-red-400'}`}
            >
              {result.compliant ? 'COMPLIANT' : 'EXCEEDED'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Margin</span>
            <span
              className={
                result.margin_db >= 0 ? 'text-green-400' : 'text-red-400'
              }
            >
              {result.margin_db > 0 ? '+' : ''}
              {result.margin_db.toFixed(1)} dB
            </span>
          </div>
          {result.max_tx_power_dbm != null && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Max TX power</span>
              <span className="text-blue-300">
                {result.max_tx_power_dbm.toFixed(1)} dBm
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

export default function AnalysisPanel() {
  const [openSection, setOpenSection] = useState<string | null>('power')

  function toggle(key: string) {
    setOpenSection((prev) => (prev === key ? null : key))
  }

  return (
    <div>
      <Section
        title="Power sweep"
        open={openSection === 'power'}
        onToggle={() => toggle('power')}
      >
        <PowerSweepSection />
      </Section>
      <Section
        title="Frequency sweep"
        open={openSection === 'freq'}
        onToggle={() => toggle('freq')}
      >
        <FrequencySweepSection />
      </Section>
      <Section
        title="Link budget"
        open={openSection === 'link'}
        onToggle={() => toggle('link')}
      >
        <LinkBudgetSection />
      </Section>
    </div>
  )
}
