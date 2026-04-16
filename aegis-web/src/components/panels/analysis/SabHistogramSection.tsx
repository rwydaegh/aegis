import { useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  Cell,
} from 'recharts'
import { useActiveSimulation } from '@/hooks/useActiveSimulation'
import { computeHistogram, formatSabNumber } from './utils'

// ---------------------------------------------------------------------------
// SAB histogram section (client-side)
// ---------------------------------------------------------------------------

export function SabHistogramSection() {
  const { sabArray, stats } = useActiveSimulation()

  const histogram = useMemo(() => {
    if (!sabArray || sabArray.length === 0) return null
    return computeHistogram(sabArray, 24)
  }, [sabArray])

  if (!histogram || histogram.bins.length === 0 || !stats) {
    return (
      <span className="text-[10px] text-muted-foreground/50">
        Run a compute first
      </span>
    )
  }

  const limit = stats.compliance?.checks?.find(c => c.label.includes('4 cm'))?.limit
  const chartData = histogram.bins.map((b, i) => ({
    idx: i,
    count: b.count,
    label: b.label,
    x0: b.x0,
    x1: b.x1,
    aboveLimit: limit != null && b.x0 >= limit,
  }))

  return (
    <div>
      <p className="text-[10px] text-muted-foreground/60 mb-2">
        Distribution of S_ab across illuminated triangles (log-scale bins).
      </p>
      <ResponsiveContainer width="100%" height={130}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 16, left: 0 }}>
          <XAxis
            dataKey="label"
            tick={{ fontSize: 8, fill: '#888' }}
            interval={Math.max(0, Math.floor(chartData.length / 5) - 1)}
            label={{
              value: 'S_ab (W/m\u00B2)',
              position: 'bottom',
              fontSize: 9,
              fill: '#666',
              offset: 0,
            }}
          />
          <YAxis
            tick={{ fontSize: 9, fill: '#888' }}
            width={35}
            label={{
              value: 'triangles',
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
            formatter={(value) => [Number(value).toLocaleString(), 'Triangles']}
            labelFormatter={(_label, payload) => {
              const d = (payload as unknown as Array<{ payload?: { x0: number; x1: number } }>)?.[0]?.payload
              if (!d) return ''
              return `${formatSabNumber(d.x0)} - ${formatSabNumber(d.x1)} W/m\u00B2`
            }}
          />
          {limit != null && (
            <ReferenceLine
              x={chartData.findIndex(d => d.x0 >= limit)}
              stroke="#f87171"
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{ value: 'limit', position: 'top', fontSize: 8, fill: '#f87171' }}
            />
          )}
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {chartData.map((entry, idx) => (
              <Cell
                key={idx}
                fill={entry.aboveLimit ? '#f87171' : '#4ade80'}
                fillOpacity={0.7}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: 'rgba(74,222,128,0.7)' }} />
          Below limit
        </span>
        {limit != null && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ background: 'rgba(248,113,113,0.7)' }} />
            Above limit
          </span>
        )}
      </div>
    </div>
  )
}
