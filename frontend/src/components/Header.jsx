function dot(color) {
  return <span className="dot" style={{ background: color }} />
}

export default function Header({ status, connected, source, modelSource, fault }) {
  const link =
    status === 'open'
      ? connected
        ? { c: '#2ee6a6', t: 'Live' }
        : { c: '#f5b342', t: 'Backend up · no device' }
      : status === 'connecting'
        ? { c: '#f5b342', t: 'Connecting…' }
        : { c: '#ff5a5a', t: 'Backend offline' }

  const isSim = source === 'SIMULATOR'

  return (
    <header className="header">
      <div className="brand">
        <div className={'brand-mark' + (fault ? ' fault' : '')}>⚙</div>
        <div>
          <h1>Motor Fault Detection</h1>
          <p>Real-time predictive maintenance · Arduino + ML</p>
        </div>
      </div>

      <div className="status-cluster">
        <div className="status-pill">
          {dot(link.c)} <span>{link.t}</span>
        </div>
        <div className="status-pill">
          {dot(isSim ? '#7aa2ff' : '#2ee6a6')}
          <span>{isSim ? 'Simulator' : source || 'No source'}</span>
        </div>
        <div className="status-pill">
          {dot(modelSource?.startsWith('loaded') ? '#2ee6a6' : '#9aa4b2')}
          <span>{modelSource?.startsWith('loaded') ? 'ML model' : 'Heuristic model'}</span>
        </div>
      </div>
    </header>
  )
}
