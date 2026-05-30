// Compact live metric tile with a value, unit, and a fill bar vs its range.
export default function MetricCard({ label, unit, value, min = 0, max = 100 }) {
  const v = typeof value === 'number' ? value : null
  const pct = v == null ? 0 : Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100))

  // Warn/critical tint when a metric is near the top of its range.
  const tone = pct >= 90 ? 'crit' : pct >= 75 ? 'warn' : 'ok'

  return (
    <div className={'metric-card tone-' + tone}>
      <div className="metric-top">
        <span className="metric-label">{label}</span>
        <span className="metric-unit">{unit}</span>
      </div>
      <div className="metric-value">{v == null ? '—' : fmt(v)}</div>
      <div className="metric-bar">
        <div className="metric-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function fmt(v) {
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString()
  if (Math.abs(v) >= 100) return v.toFixed(0)
  return v.toFixed(2)
}
