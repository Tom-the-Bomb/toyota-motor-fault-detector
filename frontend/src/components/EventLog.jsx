function clock(t) {
  const s = Math.max(0, (Date.now() - t * 1000) / 1000)
  if (s < 60) return `${Math.round(s)}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  return `${Math.round(s / 3600)}h ago`
}

export default function EventLog({ events, onClear }) {
  return (
    <section className="section">
      <div className="section-head">
        <span className="label">Fault log</span>
        {events.length > 0
          ? <button className="clear" onClick={onClear}>clear</button>
          : <span className="count">{events.length} entries</span>}
      </div>
      <div className="log-list">
        {events.length === 0 && <div className="log-empty">No faults recorded.</div>}
        {events.map((e) => (
          <div key={e.id} className="log-row">
            <span className="when">{clock(e.t)}</span>
            <span className="what">{e.type}</span>
            <span className="vals">
              health {Math.round(e.health)}
              {e.probability != null && ` · p ${(e.probability * 100).toFixed(0)}%`}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
