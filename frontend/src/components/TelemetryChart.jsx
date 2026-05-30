import { Line, LineChart, ResponsiveContainer, Tooltip, YAxis } from 'recharts'

// Simple, standard line colors.
const COLORS = {
  current: '#2563eb',
  voltage: '#0891b2',
  temperature: '#ea580c',
  rpm: '#16a34a',
  torque: '#7c3aed',
  load: '#ca8a04',
  vibration: '#db2777',
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
              cursor={{ stroke: '#d1d5db', strokeWidth: 1 }}
              contentStyle={{
                background: '#ffffff',
                border: '1px solid #c9cdd2',
                borderRadius: 0,
                fontSize: 12,
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
