import { useTelemetry } from './lib/useTelemetry'
import Header from './components/Header'
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

  // per-metric value series for the inline sparklines
  const seriesFor = (k) => history.map((s) => s.telemetry?.[k] ?? null)

  return (
    <div className="page">
      <div className="panel">
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

        {/* hero: verdict | health | fault probability */}
        <div className="hero">
          <div className={'hero-verdict ' + (isFault ? 'bad' : 'ok')}>
            <span className="label">State</span>
            <div className="verdict-word">
              {isFault ? 'Fault predicted' : 'Operating normally'}
            </div>
            <div className="verdict-detail">
              {isFault
                ? (latest?.fault_type || 'anomaly').toLowerCase()
                : 'within nominal parameters'}
            </div>
          </div>

          <div className="hero-stats">
            <div className="stat">
              <span className="label">Health</span>
              <div
                className="stat-num"
                style={{ color: isFault ? 'var(--fault)' : 'var(--ink)' }}
              >
                {Math.round(health)}
                <span className="stat-of">/100</span>
              </div>
              <div className="bar">
                <span
                  style={{
                    width: `${Math.max(0, Math.min(100, health))}%`,
                    background: isFault ? 'var(--fault)' : 'var(--ink)',
                  }}
                />
              </div>
            </div>
            <div className="stat">
              <span className="label">Fault probability</span>
              <div className="stat-num">
                {prob != null ? (prob * 100).toFixed(1) : '——'}
                <span className="stat-of">%</span>
              </div>
              <div className="readout-meta">
                {connected ? source?.toLowerCase() || 'unknown source' : 'device not connected'}
              </div>
            </div>
          </div>
        </div>

        {/* telemetry register */}
        <section className="module">
          <div className="module-head">
            <span className="label">Telemetry</span>
            <span className="count">{metricKeys.length} channels</span>
          </div>
          <div className="register">
            {metricKeys.map((k) => (
              <MetricCard
                key={k}
                label={metrics[k].label}
                unit={metrics[k].unit}
                value={telemetry[k]}
                series={seriesFor(k)}
                min={metrics[k].min}
                max={metrics[k].max}
              />
            ))}
          </div>
        </section>

        {/* signal history */}
        <section className="module">
          <div className="module-head">
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

        {/* fault log */}
        <EventLog events={events} onClear={clearEvents} />
      </div>

      <div className="colophon">
        motor fault detection · {connected ? 'device connected' : 'no device'} · stream {status}
      </div>
    </div>
  )
}
