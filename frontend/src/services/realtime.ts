// Frontend event bus for real-time UI updates.
//
// The `useWebSocket` hook listens on the WebSocket connection and re-emits decoded
// messages through this bus. Components subscribe via `useRealTimeRefresh` to
// refetch their data whenever a relevant `data_changed` event arrives, so the
// UI stays in sync without a page reload.

type Listener = (payload: DataChangedEvent) => void

export interface DataChangedEvent {
  event: 'data_changed'
  category: string
  data: Record<string, unknown>
  timestamp: string
}

const listeners: Record<string, Set<Listener>> = {}

export const realtime = {
  on(event: string, cb: Listener): Listener {
    const set = listeners[event] ?? new Set<Listener>()
    set.add(cb)
    listeners[event] = set
    return cb
  },
  off(event: string, cb: Listener): void {
    listeners[event]?.delete(cb)
  },
  emit(event: string, payload: DataChangedEvent): void {
    listeners[event]?.forEach((cb) => cb(payload))
  },
}
