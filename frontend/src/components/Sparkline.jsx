// Tiny dependency-free SVG sparkline. Crisp at any width via non-scaling stroke.
export default function Sparkline({ data = [], color = 'var(--ink)', height = 30 }) {
  const pts = data.filter((v) => typeof v === 'number')
  const W = 200 // virtual coordinate width; SVG scales to its container
  if (pts.length < 2) {
    return <svg className="spark" viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none" />
  }
  const min = Math.min(...pts)
  const max = Math.max(...pts)
  const span = max - min || 1
  const step = W / (pts.length - 1)
  const line = pts
    .map((v, i) => `${(i * step).toFixed(1)},${(height - 1 - ((v - min) / span) * (height - 2)).toFixed(1)}`)
    .join(' ')

  return (
    <svg className="spark" viewBox={`0 0 ${W} ${height}`} preserveAspectRatio="none">
      <polyline
        points={line}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
