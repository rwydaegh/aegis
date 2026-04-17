import { useOptimizeStore, type OptimizeMode } from '@/stores/optimize'
import { useOptimization } from '@/hooks/useOptimization'
import { useSimulationStore } from '@/stores/simulation'
import { useMIMOStore } from '@/stores/mimo'
import { LineChart, Line, YAxis, ResponsiveContainer } from 'recharts'

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
  onToggle: (value: OptimizeMode) => void
}

function ModeSelector({ mode, running, mimoEnabled, onToggle }: ModeSelectorProps) {
  return (
    <div className="grid grid-cols-3 gap-1">
      {MODES.map(m => {
        const disabled = running || (m.value === 'mimo_peak' && !mimoEnabled)
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
            title={m.description}
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
  return (
    <div className="space-y-1">
      <div className="w-full h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground text-center">
        Evaluating position {currentIter} of {total}
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

  const { start, stop } = useOptimization()

  const canRun = antennaPos !== null && mode !== null && !running
  const canRunMimo = mimoEnabled && mode === 'mimo_peak'
  const canRunOther = mode !== null && mode !== 'mimo_peak'
  const enabled = canRun && (canRunMimo || canRunOther)

  const chartData = history.map(h => ({ iter: h.iter, value: h.objective }))

  const gridSize = constraints.gridSize ?? 5
  const gridSpacing = constraints.gridSpacing ?? 2

  return (
    <div className="space-y-3 text-sm">
      <ModeSelector
        mode={mode}
        running={running}
        mimoEnabled={mimoEnabled}
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
        <div className="h-16">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <YAxis domain={['auto', 'auto']} hide />
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--primary))"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {summary && (
        <p className="text-xs text-muted-foreground bg-muted/50 rounded px-2 py-1.5">
          {summary}
        </p>
      )}
    </div>
  )
}
