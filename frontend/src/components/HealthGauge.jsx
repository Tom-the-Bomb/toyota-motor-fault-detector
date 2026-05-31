// Circular SVG gauge showing motor health 0–100 (no chart lib needed).
export default function HealthGauge({ health = 0, prediction = 'healthy' }) {
  const v = Math.max(0, Math.min(100, Math.round(health)))
  const R = 88
  const C = 2 * Math.PI * R
  const dash = (v / 100) * C

  const color = v >= 70 ? '#2ee6a6' : v >= 40 ? '#f5b342' : '#ff5a5a'
  const isFault = prediction === 'fault'

  return (
    <div className="gauge">
      <svg viewBox="0 0 220 220" width="100%" height="100%">
        <circle cx="110" cy="110" r={R} className="gauge-track" />
        <circle
          cx="110"
          cy="110"
          r={R}
          className="gauge-value"
          stroke={color}
          strokeDasharray={`${dash} ${C}`}
          transform="rotate(-90 110 110)"
        />
        <text x="110" y="100" className="gauge-num" fill={color}>{v}</text>
        <text x="110" y="128" className="gauge-unit">HEALTH</text>
        <text x="110" y="152" className="gauge-state" fill={color}>
          {isFault ? 'FAULT' : 'NOMINAL'}
        </text>
      </svg>
    </div>
  )
}
