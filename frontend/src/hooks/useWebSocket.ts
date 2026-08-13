import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../store/authStore'
import { realtime, type DataChangedEvent } from '../services/realtime'

const API_URL = '/api'
const RECONNECT_CAP_MS = 30000

export function useWebSocket() {
  const token = useAuth((state) => state.token)
  const isAuthenticated = useAuth((state) => state.isAuthenticated)
  const [connected, setConnected] = useState(false)
  const [reconnectKey, setReconnectKey] = useState(0)
  const pingRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const clearPing = () => {
    if (pingRef.current) {
      clearInterval(pingRef.current)
      pingRef.current = null
    }
  }

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setConnected(false)
      return
    }

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}${API_URL}/ws?token=${encodeURIComponent(token)}`

    const ws = new WebSocket(url)

    ws.onopen = () => {
      setConnected(true)
      // Lightweight ping so the server can reap backgrounded/suspended tabs.
      pingRef.current = window.setInterval(() => {
        try {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        } catch {
          /* ignore send failures during teardown */
        }
      }, 25000)
    }

    ws.onmessage = (ev) => {
      let msg: any
      try {
        msg = JSON.parse(ev.data)
      } catch {
        return
      }
      if (msg.event === 'connected') {
        realtime.emit('connected', msg)
      } else if (msg.event === 'data_changed') {
        realtime.emit('data_changed', msg as DataChangedEvent)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      clearPing()
      const backoff = Math.min(1000 * Math.pow(2, reconnectKey), RECONNECT_CAP_MS)
      window.setTimeout(() => setReconnectKey((k) => k + 1), backoff)
    }

    ws.onerror = () => {
      try {
        ws.close()
      } catch {
        /* ignore */
      }
    }

    return () => {
      clearPing()
      try {
        ws.close()
      } catch {
        /* ignore */
      }
    }
  }, [token, isAuthenticated, reconnectKey])

  return { connected }
}
