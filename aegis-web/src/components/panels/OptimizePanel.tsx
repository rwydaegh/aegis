import { useOptimizeStore, type OptimizeMode } from '@/stores/optimize'
import { useOptimization } from '@/hooks/useOptimization'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { useSceneStore } from '@/stores/scene'
import { useUIStore } from '@/stores/ui'
import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts'
import HistoryScrubber from './HistoryScrubber'

const MODES: { value: OptimizeMode; label: string; description: string }[] = [
  {
    value: 'placement',
    label: 'Placement',
    description: 'Grid search for optimal antenna position',
  },
  {
    value: 'tilt_power',
    label: 'Tilt + power',
    description: 'Maximize TX power within ICNIRP limits',
  },
  {
    value: 'mimo_peak',
    label: 'MIMO peak',
    description: 'Minimize peak S_ab via precoder optimization',
  },
]

interface ModeSelectorProps {
  mode: OptimizeMode | null
  running: boolean
  mimoEnabled: boolean
  mimoReady: boolean
  rtReady: boolean
  onToggle: (value: OptimizeMode) => void
}

function ModeSelector({ mode, running, mimoEnabled, mimoReady, rtReady, onToggle }: ModeSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-1">
      {MODES.map(m => {
        const needsRt = m.value === 'tilt_power' && !rtReady
        const needsMimo = m.value === 'mimo_peak' && !mimoEnabled
        const needsMimoReady = m.value === 'mimo_peak' && mimoEnabled && !mimoReady
        const disabled = running || needsMimo || needsMimoReady || needsRt
        const title = needsRt
          ? 'Requires a ray-traced scene. Run an RT compute first.'
          : needsMimoReady
            ? 'MIMO scene is still computing. Wait for the compute to finish.'
            : m.description
        return (
          <button
            key={m.value}
            onClick={() => onToggle(m.value)}
            disabled={disabled}
            className={`px-2 py-1.5 rounded text-xs font-medium transition-colors
              ${
                mode === m.value
                  ? 'bg-primary text-primary-foreground border border-primary'
                  : 'bg-muted text-muted-foreground border border-border hover:bg-muted/80'
              }
              ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
            title={title}
          >
            {m.label}
          </button>
        )
      })}
    </div>
  )
}

interface ModeDescriptionProps {
  mode: OptimizeMode | null
  antennaPos: [number, number, number] | null
  gridSize: number
  gridSpacing: number
}

function ModeDescription({ mode, antennaPos, gridSize, gridSpacing }: ModeDescriptionProps) {
  if (!mode) {
    return (
      <p className="text-xs text-muted-foreground">
        Select a strategy to optimize antenna configuration for minimum exposure.
      </p>
    )
  }
  return (
    <>
      {mode === 'placement' && (
        <p className="text-xs text-muted-foreground">
          Evaluates a {gridSize}&times;{gridSize} grid
          ({gridSize ** 2} positions) centered on the current antenna,
          spaced {gridSpacing}m apart. Selects the position with the
          lowest peak S<sub>ab</sub>. The grid is previewed in the 3D view.
        </p>
      )}
      {mode === 'tilt_power' && (
        <p className="text-xs text-muted-foreground">
          Iteratively adjusts antenna downtilt and transmit power to maximize
          coverage while keeping peak S<sub>ab</sub> below the ICNIRP limit.
          Requires a ray-traced scene.
        </p>
      )}
      {mode === 'mimo_peak' && (
        <p className="text-xs text-muted-foreground">
          Optimizes MIMO precoder weights to minimize peak S<sub>ab</sub> across
          all users within the specified power budget.
        </p>
      )}
      {mode === 'placement' && !antennaPos && (
        <p className="text-xs text-amber-400/80">
          Click in the 3D view to place the antenna before optimizing.
        </p>
      )}
    </>
  )
}

interface ModeConstraintsProps {
  mode: OptimizeMode | null
  running: boolean
  icnirpLimit: number
  pMax: number
  gridSize: number
  gridSpacing: number
  onSetConstraints: (c: Partial<{ icnirpLimit: number; pMax: number; gridSize: number; gridSpacing: number }>) => void
}

function ModeConstraints({
  mode, running, icnirpLimit, pMax, gridSize, gridSpacing, onSetConstraints,
}: ModeConstraintsProps) {
  if (mode === 'tilt_power') {
    return (
      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">ICNIRP limit (W/m²)</label>
        <input
          type="number"
          value={icnirpLimit}
          onChange={e => {
            const v = parseFloat(e.target.value)
            if (!isNaN(v)) onSetConstraints({ icnirpLimit: v })
          }}
          disabled={running}
          className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
        />
      </div>
    )
  }
  if (mode === 'mimo_peak') {
    return (
      <div className="space-y-1">
        <label className="text-xs text-muted-foreground">Power budget (||x||²)</label>
        <input
          type="number"
          value={pMax}
          onChange={e => {
            const v = parseFloat(e.target.value)
            if (!isNaN(v)) onSetConstraints({ pMax: v })
          }}
          disabled={running}
          className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
          step={0.1}
        />
      </div>
    )
  }
  if (mode === 'placement') {
    return (
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Grid size</label>
          <input
            type="number"
            value={gridSize}
            onChange={e => {
              const v = parseInt(e.target.value)
              if (!isNaN(v)) onSetConstraints({ gridSize: v })
            }}
            disabled={running}
            className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
            min={3}
            max={9}
            step={2}
          />
        </div>
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Spacing (m)</label>
          <input
            type="number"
            value={gridSpacing}
            onChange={e => {
              const v = parseFloat(e.target.value)
              if (!isNaN(v)) onSetConstraints({ gridSpacing: v })
            }}
            disabled={running}
            className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
            step={0.5}
          />
        </div>
      </div>
    )
  }
  return null
}

interface PlacementProgressProps {
  currentIter: number
  total: number
}

function PlacementProgress({ currentIter, total }: PlacementProgressProps) {
  const pct = Math.min(100, (currentIter / total) * 100)
  const indeterminate = currentIter === 0
  return (
    <div className="space-y-1">
      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden relative">
        {indeterminate ? (
          <div className="absolute inset-y-0 w-1/3 bg-primary/70 rounded-full animate-[pulse_1.4s_ease-in-out_infinite]" />
        ) : (
          <div
            className="h-full bg-primary rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      <p className="text-xs text-muted-foreground text-center">
        {indeterminate
          ? 'Preparing ray tracer and scene…'
          : `Evaluating position ${currentIter} of ${total}`}
      </p>
    </div>
  )
}

export default function OptimizePanel() {
  const mode = useOptimizeStore(s => s.mode)
  const setMode = useOptimizeStore(s => s.setMode)
  const constraints = useOptimizeStore(s => s.constraints)
  const setConstraints = useOptimizeStore(s => s.setConstraints)
  const running = useOptimizeStore(s => s.running)
  const currentIter = useOptimizeStore(s => s.currentIter)
  const history = useOptimizeStore(s => s.history)
  const summary = useOptimizeStore(s => s.summary)

  const antennaPos = useSimulationStore(s => s.antennaPos)
  const mimoEnabled = useMIMOStore(s => s.enabled)
  const mimoSummary = useMIMOStore(s => s.summaryStats)
  const isComputing = useUIStore(s => s.isComputing)
  const rtReady = useSceneStore(s => s.rtPaths !== null && s.rtPaths.length > 0)

  // MIMO peak needs a cached mimo_scene on the server. summaryStats is set only
  // after a successful compute, and !isComputing avoids the recompute race that
  // clears/stales the backend cache while the store still thinks MIMO is on.
  const mimoReady = mimoSummary !== null && !isComputing

  const { start, stop } = useOptimization()

  // Only placement needs a single antennaPos; MIMO uses the MIMO array (checked via mimoEnabled/mimoReady)
  // and tilt_power reads cached RT paths (checked via rtReady).
  const canRun = mode !== null && !running
  const canRunMimo = mode === 'mimo_peak' && mimoEnabled && mimoReady
  const canRunTiltPower = mode === 'tilt_power' && rtReady
  const canRunPlacement = mode === 'placement' && antennaPos !== null
  const enabled = canRun && (canRunMimo || canRunTiltPower || canRunPlacement)

  const chartData = history.map(h => ({ iter: h.iter, value: h.objective }))

  const gridSize = constraints.gridSize ?? 5
  const gridSpacing = constraints.gridSpacing ?? 2

  return (
    <div className="space-y-3 text-sm">
      <ModeSelector
        mode={mode}
        running={running}
        mimoEnabled={mimoEnabled}
        mimoReady={mimoReady}
        rtReady={rtReady}
        onToggle={value => setMode(mode === value ? null : value)}
      />

      <ModeDescription
        mode={mode}
        antennaPos={antennaPos}
        gridSize={gridSize}
        gridSpacing={gridSpacing}
      />

      <ModeConstraints
        mode={mode}
        running={running}
        icnirpLimit={constraints.icnirpLimit ?? 20}
        pMax={constraints.pMax ?? 1}
        gridSize={gridSize}
        gridSpacing={gridSpacing}
        onSetConstraints={setConstraints}
      />

      <button
        onClick={running ? stop : start}
        disabled={!running && !enabled}
        className={`w-full py-2 rounded text-xs font-semibold transition-colors
          ${
            running
              ? 'bg-red-600 hover:bg-red-700 text-white'
              : enabled
                ? 'bg-primary hover:bg-primary/90 text-primary-foreground'
                : 'bg-muted text-muted-foreground opacity-40 cursor-not-allowed'
          }`}
      >
        {running ? `Stop (iter ${currentIter})` : 'Optimize'}
      </button>

      {running && mode === 'placement' && (
        <PlacementProgress currentIter={currentIter} total={gridSize ** 2} />
      )}

      {history.length > 1 && (
        <div>
          <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">
            Peak S<sub>ab</sub> per iteration
          </p>
          <div className="h-16">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <YAxis domain={['auto', 'auto']} hide />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="var(--color-primary)"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3, fill: 'var(--color-primary)', stroke: 'var(--color-foreground)' }}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {summary && (
        <p className="text-xs text-muted-foreground bg-muted/50 rounded px-2 py-1.5">
          {summary}
        </p>
      )}

      {!running && mode === 'placement' && history.length > 1 && <HistoryScrubber />}
    </div>
  )
}
