import { useTelemetry } from './lib/useTelemetry'
import Header from './components/Header'
import FaultBanner from './components/FaultBanner'
import MetricCard from './components/MetricCard'
import TelemetryChart from './components/TelemetryChart'
import EventLog from './components/EventLog'

const CHART_METRICS = ['current', 'voltage']

export default function App() {
  const { status, latest, history, meta, events, source, connected, clearEvents } =
    useTelemetry()

  const metrics = meta?.metrics || {}
  const telemetry = latest?.telemetry || {}
  const metricKeys = Object.keys(metrics)
  const health = latest?.health ?? 100
  const prob = latest?.probability
  const isFault = latest?.prediction === 'fault'

  return (
    <div className="page">
      <Header
        status={status}
        connected={connected}
        source={source}
        modelSource={meta?.model_source}
      />

      {status !== 'open' && (
        <div className="offline">
          waiting for backend at ws://localhost:8000/ws — start it with{' '}
          <code>uv run python app.py</code>
        </div>
      )}

      <FaultBanner latest={latest} />

      {/* hero readout */}
      <div className="readout">
        <div className="health-block">
          <span className="label">Motor health index</span>
          <div className="health-figure">
            <span
              className="health-num"
              style={{ color: isFault ? 'var(--fault)' : 'var(--ink)' }}
            >
              {Math.round(health)}
            </span>
            <span className="health-of">/ 100</span>
          </div>
          <div className="bar">
            <span
              style={{
                width: `${Math.max(0, Math.min(100, health))}%`,
                background: isFault ? 'var(--fault)' : 'var(--ok)',
              }}
            />
          </div>
          <span className="readout-meta">
            {latest
              ? `${history.length} samples · ${meta?.model_source || 'model'}`
              : 'awaiting telemetry'}
          </span>
        </div>

        <div className="prob-block">
          <span className="label">Fault probability</span>
          <div className="prob-figure">
            {prob != null ? (prob * 100).toFixed(1) : '—'}
            <small>%</small>
          </div>
          <span className="readout-meta">
            {connected ? `source · ${source || 'unknown'}` : 'device not connected'}
          </span>
        </div>
      </div>

      {/* metrics register */}
      <section className="section">
        <div className="section-head">
          <span className="label">Live telemetry</span>
          <span className="count">{metricKeys.length} channels</span>
        </div>
        <div className="register">
          {metricKeys.map((k) => (
            <MetricCard
              key={k}
              label={metrics[k].label}
              unit={metrics[k].unit}
              value={telemetry[k]}
              min={metrics[k].min}
              max={metrics[k].max}
            />
          ))}
        </div>
      </section>

      {/* signal history */}
      <section className="section">
        <div className="section-head">
          <span className="label">Signal history</span>
          <span className="count">{history.length} pts</span>
        </div>
        <div className="signals">
          {CHART_METRICS.filter((k) => metrics[k]).map((k) => (
            <TelemetryChart
              key={k}
              history={history}
              metricKey={k}
              label={metrics[k].label}
              unit={metrics[k].unit}
            />
          ))}
        </div>
      </section>

      <EventLog events={events} onClear={clearEvents} />

      <div className="colophon">
        motor fault detection · {connected ? 'device connected' : 'no device'} · stream {status}
      </div>
    </div>
  )
}
