import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Connects to the Flask backend's /ws WebSocket and exposes live telemetry.
 *
 * Returns:
 *   status      'connecting' | 'open' | 'closed'
 *   latest      most recent sample { t, telemetry, prediction, fault_type, probability, health }
 *   history     array of recent samples (for charts)
 *   meta        { metrics, model_source, ... } from the backend
 *   source      backend data source: serial port string or "SIMULATOR"
 *   events      derived alert log (fault episodes)
 */
const DEFAULT_URL =
  (location.protocol === 'https:' ? 'wss://' : 'ws://') +
  (location.hostname || 'localhost') +
  ':8000/ws'

const MAX_POINTS = 400

export function useTelemetry(url = DEFAULT_URL) {
  const [status, setStatus] = useState('connecting')
  const [latest, setLatest] = useState(null)
  const [history, setHistory] = useState([])
  const [meta, setMeta] = useState(null)
  const [events, setEvents] = useState([])
  const wsRef = useRef(null)
  const reconnectRef = useRef(null)
  const prevFault = useRef(false)

  const pushEvent = useCallback((sample) => {
    const isFault = sample.prediction === 'fault'
    if (isFault && !prevFault.current) {
      setEvents((e) =>
        [{
          id: `${sample.t}-${Math.round(sample.health)}`,
          t: sample.t,
          type: sample.fault_type || 'fault',
          health: sample.health,
          probability: sample.probability,
          telemetry: sample.telemetry,
        }, ...e].slice(0, 50),
      )
    }
    prevFault.current = isFault
  }, [])

  const connect = useCallback(() => {
    setStatus('connecting')
    let ws
    try {
      ws = new WebSocket(url)
    } catch {
      setStatus('closed')
      scheduleReconnect()
      return
    }
    wsRef.current = ws

    ws.onopen = () => setStatus('open')
    ws.onclose = () => {
      setStatus('closed')
      scheduleReconnect()
    }
    ws.onerror = () => ws.close()
    ws.onmessage = (ev) => {
      let msg
      try {
        msg = JSON.parse(ev.data)
      } catch {
        return
      }
      if (msg.type === 'meta') {
        setMeta(msg)
        if (Array.isArray(msg.history) && msg.history.length) {
          setHistory(msg.history.slice(-MAX_POINTS))
        }
      } else if (msg.type === 'sample') {
        setLatest(msg)
        setHistory((h) => [...h, msg].slice(-MAX_POINTS))
        pushEvent(msg)
      }
    }
  }, [url, pushEvent])

  const scheduleReconnect = useCallback(() => {
    clearTimeout(reconnectRef.current)
    reconnectRef.current = setTimeout(connect, 1500)
  }, [connect])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    status,
    latest,
    history,
    meta,
    events,
    source: latest?.port || meta?.port || null,
    connected: latest?.connected ?? meta?.connected ?? false,
    clearEvents: () => setEvents([]),
  }
}
