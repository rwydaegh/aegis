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

export default function OptimizePanel() {
  const mode = useOptimizeStore((s) => s.mode)
  const setMode = useOptimizeStore((s) => s.setMode)
  const constraints = useOptimizeStore((s) => s.constraints)
  const setConstraints = useOptimizeStore((s) => s.setConstraints)
  const running = useOptimizeStore((s) => s.running)
  const currentIter = useOptimizeStore((s) => s.currentIter)
  const history = useOptimizeStore((s) => s.history)
  const summary = useOptimizeStore((s) => s.summary)

  const antennaPos = useSimulationStore((s) => s.antennaPos)
  const mimoEnabled = useMIMOStore((s) => s.enabled)

  const { start, stop } = useOptimization()

  const canRun = antennaPos !== null && mode !== null && !running
  const canRunMimo = mimoEnabled && mode === 'mimo_peak'
  const canRunOther = mode !== null && mode !== 'mimo_peak'
  const enabled = canRun && (canRunMimo || canRunOther)

  const chartData = history.map((h) => ({ iter: h.iter, value: h.objective }))

  return (
    <div className="space-y-3 text-sm">
      {/* Mode selector */}
      <div className="grid grid-cols-3 gap-1">
        {MODES.map((m) => (
          <button
            key={m.value}
            onClick={() => setMode(mode === m.value ? null : m.value)}
            disabled={running || (m.value === 'mimo_peak' && !mimoEnabled)}
            className={`px-2 py-1.5 rounded text-xs font-medium transition-colors
              ${
                mode === m.value
                  ? 'bg-primary text-primary-foreground border border-primary'
                  : 'bg-muted text-muted-foreground border border-border hover:bg-muted/80'
              }
              ${running || (m.value === 'mimo_peak' && !mimoEnabled) ? 'opacity-40 cursor-not-allowed' : ''}`}
            title={m.description}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Mode description */}
      {mode && (
        <p className="text-xs text-muted-foreground">
          {MODES.find((m) => m.value === mode)?.description}
        </p>
      )}

      {/* Mode-specific constraints */}
      {mode === 'tilt_power' && (
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">
            ICNIRP limit (W/m²)
          </label>
          <input
            type="number"
            value={constraints.icnirpLimit ?? 20}
            onChange={(e) =>
              setConstraints({ icnirpLimit: parseFloat(e.target.value) })
            }
            disabled={running}
            className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
          />
        </div>
      )}

      {mode === 'mimo_peak' && (
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">
            Power budget (||x||²)
          </label>
          <input
            type="number"
            value={constraints.pMax ?? 1}
            onChange={(e) =>
              setConstraints({ pMax: parseFloat(e.target.value) })
            }
            disabled={running}
            className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
            step={0.1}
          />
        </div>
      )}

      {mode === 'placement' && (
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">Grid size</label>
            <input
              type="number"
              value={constraints.gridSize ?? 5}
              onChange={(e) =>
                setConstraints({ gridSize: parseInt(e.target.value) })
              }
              disabled={running}
              className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
              min={3}
              max={9}
              step={2}
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">
              Spacing (m)
            </label>
            <input
              type="number"
              value={constraints.gridSpacing ?? 2}
              onChange={(e) =>
                setConstraints({ gridSpacing: parseFloat(e.target.value) })
              }
              disabled={running}
              className="w-full px-2 py-1 bg-muted border border-border rounded text-xs"
              step={0.5}
            />
          </div>
        </div>
      )}

      {/* Run / Stop button */}
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

      {/* Convergence sparkline */}
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
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <p className="text-xs text-muted-foreground bg-muted/50 rounded px-2 py-1.5">
          {summary}
        </p>
      )}
    </div>
  )
}
