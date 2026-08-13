import { render, act } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import React from 'react'

import { useWebSocket } from './useWebSocket'
import { realtime } from '../services/realtime'

vi.mock('../services/realtime', () => ({
  realtime: { emit: vi.fn(), on: vi.fn(), off: vi.fn() },
}))

vi.mock('../store/authStore', () => ({
  useAuth: (selector: (s: any) => any) =>
    selector({ token: 'test-token', isAuthenticated: true, user: { id: 1 } }),
}))

class FakeWebSocket {
  static OPEN = 1
  static CLOSED = 3
  static lastInstance: FakeWebSocket | undefined
  readyState = FakeWebSocket.OPEN
  url = ''
  onopen: (() => void) | null = null
  onclose: ((e: any) => void) | null = null
  onerror: ((e: any) => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  sent: string[] = []
  constructor(url: string) {
    this.url = url
    FakeWebSocket.lastInstance = this
  }
  send(data: string) { this.sent.push(data) }
  close() { this.readyState = FakeWebSocket.CLOSED }
  _open() { this.onopen?.() }
  _message(data: string) { this.onmessage?.({ data }) }
}

describe('useWebSocket', () => {
  const OriginalWebSocket = (globalThis as any).WebSocket

  beforeEach(() => {
    ;(globalThis as any).WebSocket = FakeWebSocket
    ;(realtime.emit as any).mockReset()
    FakeWebSocket.lastInstance = undefined
  })

  afterEach(() => {
    ;(globalThis as any).WebSocket = OriginalWebSocket
  })

  const Probe: React.FC = () => {
    useWebSocket()
    return null
  }

  it('connects to /api/ws using the auth token', () => {
    render(<Probe />)
    const ws = FakeWebSocket.lastInstance
    expect(ws).toBeDefined()
    expect(ws!.url).toMatch(/\/api\/ws\?token=test-token$/)
  })

  it('emits received data_changed events to the realtime bus', () => {
    render(<Probe />)
    const ws = FakeWebSocket.lastInstance!
    ws._open()
    ws._message(
      JSON.stringify({ event: 'data_changed', category: 'response', data: { id: 1 }, timestamp: 't' }),
    )
    expect(realtime.emit).toHaveBeenCalledWith(
      'data_changed',
      expect.objectContaining({ category: 'response' }),
    )
  })

  it('reconnects after the socket closes (schedules reconnect)', () => {
    vi.useFakeTimers()
    render(<Probe />)
    const ws = FakeWebSocket.lastInstance!
    ws._open()

    act(() => {
      ws.onclose?.({})
    })

    expect(FakeWebSocket.lastInstance).toBe(ws) // reconnect is scheduled, not immediate

    act(() => {
      vi.advanceTimersByTime(1000)
    })
    expect(FakeWebSocket.lastInstance).not.toBe(ws) // new socket created
    vi.useRealTimers()
  })
})
