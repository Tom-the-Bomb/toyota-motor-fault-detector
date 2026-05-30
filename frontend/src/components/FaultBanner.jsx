export default function FaultBanner({ latest }) {
  const isFault = latest?.prediction === 'fault'
  const faultType = latest?.fault_type

  return (
    <div className={'verdict ' + (isFault ? 'bad' : 'ok')}>
      <span className="mark">{isFault ? '✕' : '—'}</span>
      <span className="word">{isFault ? 'Fault predicted' : 'Operating normally'}</span>
      <span className="detail">
        {isFault
          ? (faultType || 'anomaly').toLowerCase()
          : 'within nominal parameters'}
      </span>
    </div>
  )
}
