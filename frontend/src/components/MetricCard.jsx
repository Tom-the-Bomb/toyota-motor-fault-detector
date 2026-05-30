import Sparkline from './Sparkline'

// One register row: name · inline sparkline · value.
export default function MetricCard({ label, unit, value, series = [], min = 0, max = 100 }) {
  const v = typeof value === 'number' ? value : null
  const pct = v == null ? 0 : Math.max(0, Math.min(100, ((v - min) / (max - min)) * 100))
  const hot = pct >= 88

  return (
    <div className={'reg-row' + (hot ? ' hot' : '')}>
      <span className="reg-name">{label}</span>
      <span className="reg-spark">
        <Sparkline data={series} color={hot ? 'var(--fault)' : 'var(--ink)'} />
      </span>
      <span className="reg-val">
        {v == null ? '——' : fmt(v)}
        <span className="u">{unit}</span>
      </span>
    </div>
  )
}

function fmt(v) {
  if (Math.abs(v) >= 1000) return Math.round(v).toLocaleString()
  if (Math.abs(v) >= 100) return v.toFixed(0)
  return v.toFixed(2)
}
