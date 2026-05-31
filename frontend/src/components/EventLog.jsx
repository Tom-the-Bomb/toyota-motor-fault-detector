function timeAgo(t) {
  const s = Math.max(0, (Date.now() - t * 1000) / 1000)
  if (s < 60) return `${Math.round(s)}s ago`
  if (s < 3600) return `${Math.round(s / 60)}m ago`
  return `${Math.round(s / 3600)}h ago`
}

export default function EventLog({ events, onClear }) {
  return (
    <div className="panel event-log">
      <div className="panel-head">
        <span>Fault Events</span>
        {events.length > 0 && (
          <button className="ghost-btn" onClick={onClear}>Clear</button>
        )}
      </div>
      <div className="event-list">
        {events.length === 0 && (
          <div className="event-empty">No faults detected yet. ✓</div>
        )}
        {events.map((e) => (
          <div key={e.id} className="event-row">
            <span className="event-tag">{e.type}</span>
            <div className="event-meta">
              <div className="event-line">
                health <strong>{Math.round(e.health)}</strong>
                {e.probability != null && (
                  <> · prob {(e.probability * 100).toFixed(0)}%</>
                )}
              </div>
              <div className="event-time">{timeAgo(e.t)}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
