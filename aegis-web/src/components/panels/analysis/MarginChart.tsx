import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  Area,
  Legend,
} from 'recharts'

// ---------------------------------------------------------------------------
// Margin chart (shared between power sweep and frequency sweep)
// ---------------------------------------------------------------------------

export interface PerCheckSeries {
  key: string
  label: string
  color: string
}

// Parallel arrays: the main tightest-margin line is always rendered. When
// `perCheck` series are supplied, each check is rendered as a thinner line
// underneath so the frequency (or power) dependence of every basic
// restriction stays legible even when one of them binds the tightest curve.
type MarginRow = {
  x: number
  margin: number | null
  compliant?: boolean
  [key: string]: number | boolean | null | undefined
}

export function MarginChart({
  data,
  xLabel,
  xUnit,
  currentX,
  maxCompliantX,
  onChartClick,
  perCheck,
}: {
  data: MarginRow[]
  xLabel: string
  xUnit: string
  currentX?: number
  maxCompliantX?: number | null
  onChartClick?: (xValue: number) => void
  perCheck?: PerCheckSeries[]
}) {
  if (data.length === 0) return null

  const allSampledValues: number[] = []
  for (const row of data) {
    const m = row.margin as number | null
    if (typeof m === 'number' && isFinite(m)) allSampledValues.push(m)
    if (perCheck) {
      for (const s of perCheck) {
        const v = row[s.key] as number | null | undefined
        if (typeof v === 'number' && isFinite(v)) allSampledValues.push(v)
      }
    }
  }
  const minMargin = allSampledValues.length > 0 ? Math.min(...allSampledValues) : -5
  const maxMargin = allSampledValues.length > 0 ? Math.max(...allSampledValues) : 5
  const yMin = Math.min(minMargin, -5)
  const yMax = Math.max(maxMargin, 5)

  return (
    <div className="mt-2">
      <ResponsiveContainer width="100%" height={perCheck ? 180 : 140}>
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
            formatter={(value, name) => {
              const v = Number(value)
              const label = typeof name === 'string' ? name : 'Margin'
              return [`${v > 0 ? '+' : ''}${v.toFixed(1)} dB`, label]
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
            name="Tightest"
            legendType="none"
            isAnimationActive={false}
          />
          {perCheck?.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              stroke={s.color}
              strokeWidth={1}
              strokeOpacity={0.75}
              dot={false}
              activeDot={{ r: 2, fill: s.color }}
              name={s.label}
              connectNulls={false}
              isAnimationActive={false}
            />
          ))}
          <Line
            type="monotone"
            dataKey="margin"
            stroke="#4ade80"
            strokeWidth={1.75}
            dot={false}
            activeDot={{ r: 3, fill: '#4ade80' }}
            name="Tightest"
            connectNulls={false}
            isAnimationActive={false}
          />
          {perCheck && (
            <Legend
              verticalAlign="bottom"
              height={24}
              iconType="plainline"
              wrapperStyle={{ fontSize: 9, color: '#888', paddingTop: 4 }}
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
