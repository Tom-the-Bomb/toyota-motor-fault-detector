import { useTelemetry } from './lib/useTelemetry'
import Header from './components/Header'
import HealthGauge from './components/HealthGauge'
import FaultBanner from './components/FaultBanner'
import MetricCard from './components/MetricCard'
import TelemetryChart from './components/TelemetryChart'
import EventLog from './components/EventLog'

// Which metrics to show as charts (the rest render as compact tiles).
const CHART_METRICS = ['current', 'rpm', 'temperature', 'vibration']

export default function App() {
  const { status, latest, history, meta, events, source, connected, clearEvents } =
    useTelemetry()

  const metrics = meta?.metrics || {}
  const telemetry = latest?.telemetry || {}
  const fault = latest?.prediction === 'fault'
  const metricKeys = Object.keys(metrics)

  const offline = status !== 'open'

  return (
    <div className={'app' + (fault ? ' app-fault' : '')}>
      <Header
        status={status}
        connected={connected}
        source={source}
        modelSource={meta?.model_source}
        fault={fault}
      />

      {offline && (
        <div className="offline-bar">
          Waiting for backend at <code>ws://localhost:8000/ws</code> — start it with{' '}
          <code>python app.py --sim</code> (or with the Arduino plugged in).
        </div>
      )}

      <FaultBanner latest={latest} meta={meta} />

      <main className="grid">
        <section className="panel gauge-panel">
          <div className="panel-head"><span>Motor Health</span></div>
          <HealthGauge health={latest?.health ?? 100} prediction={latest?.prediction} />
          <div className="gauge-foot">
            {latest
              ? `${history.length} samples · ${meta?.model_source || 'model'}`
              : 'Awaiting telemetry…'}
          </div>
        </section>

        <section className="panel metrics-panel">
          <div className="panel-head"><span>Live Telemetry</span></div>
          <div className="metric-grid">
            {metricKeys.length === 0 && (
              <div className="event-empty">No metrics yet…</div>
            )}
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

        <EventLog events={events} onClear={clearEvents} />

        <section className="panel charts-panel">
          <div className="panel-head"><span>Signal History</span></div>
          <div className="chart-grid">
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
      </main>

      <footer className="footer">
        Motor Fault Detection Dashboard · {connected ? 'device connected' : 'no device'} ·
        {' '}stream {status}
      </footer>
    </div>
  )
}
