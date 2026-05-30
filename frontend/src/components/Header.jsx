export default function Header({ status, connected, source, modelSource }) {
  const stream =
    status === 'open'
      ? connected
        ? { c: 'var(--ok)', t: 'live' }
        : { c: 'var(--muted)', t: 'no device' }
      : status === 'connecting'
        ? { c: 'var(--muted)', t: 'connecting' }
        : { c: 'var(--fault)', t: 'offline' }

  return (
    <header className="masthead">
      <div className="mast-title">
        <h1>Motor Fault Detection</h1>
        <div className="sub">predictive maintenance · arduino telemetry × ml</div>
      </div>
      <div className="statuses">
        <span className="status" style={{ color: stream.c }}>
          <span className="tick" /> {stream.t}
        </span>
        <span className="status">{source ? source.toLowerCase() : 'no source'}</span>
        <span className="status">
          {modelSource?.startsWith('loaded') ? 'ml model' : 'heuristic'}
        </span>
      </div>
    </header>
  )
}
