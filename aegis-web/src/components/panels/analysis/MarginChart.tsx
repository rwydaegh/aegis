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

// ---------------------------------------------------------------------------
// Margin chart (shared between power sweep and frequency sweep)
// ---------------------------------------------------------------------------

export function MarginChart({
  data,
  xLabel,
  xUnit,
  currentX,
  maxCompliantX,
  onChartClick,
}: {
  data: { x: number; margin: number; compliant: boolean }[]
  xLabel: string
  xUnit: string
  currentX?: number
  maxCompliantX?: number | null
  onChartClick?: (xValue: number) => void
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
          onClick={onChartClick ? (state) => {
            const idx = typeof state.activeTooltipIndex === 'number' ? state.activeTooltipIndex : -1
            if (idx >= 0 && idx < data.length) {
              onChartClick(data[idx].x)
            }
          } : undefined}
          style={onChartClick ? { cursor: 'pointer' } : undefined}
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
