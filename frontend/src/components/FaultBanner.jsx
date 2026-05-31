export default function FaultBanner({ latest, meta }) {
  const isFault = latest?.prediction === 'fault'
  const prob = latest?.probability
  const faultType = latest?.fault_type

  return (
    <div className={'fault-banner ' + (isFault ? 'is-fault' : 'is-ok')}>
      <div className="fb-icon">{isFault ? '⚠' : '✓'}</div>
      <div className="fb-body">
        <div className="fb-title">
          {isFault ? 'FAULT PREDICTED' : 'MOTOR HEALTHY'}
        </div>
        <div className="fb-sub">
          {isFault
            ? <>Detected: <strong>{faultType || 'anomaly'}</strong></>
            : 'Operating within normal parameters'}
          {prob != null && (
            <span className="fb-prob"> · fault probability {(prob * 100).toFixed(1)}%</span>
          )}
        </div>
      </div>
      {prob != null && (
        <div className="fb-meter">
          <div className="fb-meter-track">
            <div
              className="fb-meter-fill"
              style={{ width: `${Math.min(100, prob * 100)}%` }}
            />
          </div>
        </div>
      )}
    </div>
  )
}
