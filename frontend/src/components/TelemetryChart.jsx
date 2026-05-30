import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const COLORS = {
  current: '#7aa2ff',
  temperature: '#ff8a5a',
  rpm: '#2ee6a6',
  torque: '#c98aff',
  load: '#f5b342',
  vibration: '#ff5a8a',
  voltage: '#5ad1ff',
}

// `metricKey` selects which telemetry field to plot from each history sample.
export default function TelemetryChart({ history, metricKey, label, unit, faultMarks = true }) {
  const color = COLORS[metricKey] || '#7aa2ff'
  const data = history.map((s, i) => ({
    i,
    value: s.telemetry?.[metricKey] ?? null,
    fault: s.prediction === 'fault',
  }))

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
              width={44}
              tick={{ fill: '#7c8595', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                background: '#121821',
                border: '1px solid #263041',
                borderRadius: 8,
                fontSize: 12,
              }}
              labelStyle={{ display: 'none' }}
              formatter={(val) => [`${Number(val).toFixed(2)} ${unit}`, label]}
            />
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
