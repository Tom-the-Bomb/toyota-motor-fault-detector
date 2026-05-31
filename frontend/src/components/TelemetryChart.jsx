import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const COLORS = {
  current: '#7aa2ff',
  current_rise: '#c98aff',
  error: '#ff5a8a',
  temperature: '#ff8a5a',
  rpm: '#2ee6a6',
  torque: '#c98aff',
  load: '#f5b342',
  vibration: '#ff5a8a',
  voltage: '#5ad1ff',
}

// `metricKey` selects which telemetry field to plot from each history sample.
export default function TelemetryChart({ history, metricKey, label, unit, decimals, threshold }) {
  const color = COLORS[metricKey] || '#7aa2ff'
  const data = history.map((s, i) => ({
    i,
    value: s.telemetry?.[metricKey] ?? null,
    fault: s.prediction === 'fault',
  }))
  const fmt = (val) =>
    typeof decimals === 'number' ? Number(val).toFixed(decimals) : Number(val).toFixed(2)

  return (
    <div className="chart-card">
      <div className="chart-head">
        <span className="chart-title">{label}</span>
        <span className="chart-unit">{unit}</span>
      </div>
      <div className="chart-body">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
            <defs>
              <linearGradient id={`g-${metricKey}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.45} />
                <stop offset="100%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1e2633" vertical={false} />
            <XAxis dataKey="i" hide />
            <YAxis
              width={52}
              tick={{ fill: '#7c8595', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
              tickFormatter={fmt}
            />
            <Tooltip
              contentStyle={{
                background: '#121821',
                border: '1px solid #263041',
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ display: 'none' }}
              formatter={(val) => [`${fmt(val)} ${unit}`.trim(), label]}
            />
            {threshold != null && (
              <ReferenceLine
                y={threshold}
                stroke="#ff5a5a"
                strokeDasharray="4 4"
                strokeOpacity={0.8}
              />
            )}
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fill={`url(#g-${metricKey})`}
              isAnimationActive={false}
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
