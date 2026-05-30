import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from 'recharts'

// Muted, earthy line colors — no neon, no fills, no gradients.
const COLORS = {
  current: '#8fa0b3',
  temperature: '#c98a5e',
  rpm: '#9fae7e',
  torque: '#b07a8f',
  load: '#bfa46a',
  vibration: '#a98c7d',
  voltage: '#7fa0a0',
}

export default function TelemetryChart({ history, metricKey, label, unit }) {
  const color = COLORS[metricKey] || 'var(--muted)'
  const data = history.map((s, i) => ({ i, value: s.telemetry?.[metricKey] ?? null }))

  return (
    <div>
      <div className="signal-title">
        <span className="name">{label}</span>
        <span className="u">{unit}</span>
      </div>
      <div className="signal-plot">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 2, bottom: 0, left: 0 }}>
            <YAxis hide domain={['auto', 'auto']} />
            <Tooltip
              cursor={{ stroke: '#423c33', strokeWidth: 1 }}
              contentStyle={{
                background: '#14120f',
                border: '1px solid #423c33',
                borderRadius: 0,
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: 11,
                padding: '4px 8px',
              }}
              labelStyle={{ display: 'none' }}
              formatter={(val) => [`${Number(val).toFixed(2)} ${unit}`, null]}
              separator=""
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
