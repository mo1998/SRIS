import { render, act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import React from 'react'

import { realtime } from '../services/realtime'
import { useRealTimeRefresh } from './useRealTimeRefresh'

const renderHook = (cb: () => void, categories?: string[]) => {
  const refetch = vi.fn()
  const Probe: React.FC = () => {
    useRealTimeRefresh(refetch, categories)
    return null
  }
  render(<Probe />)
  return { refetch }
}

describe('useRealTimeRefresh', () => {
  it('refetches on a matching data_changed event (debounced)', () => {
    vi.useFakeTimers()
    const { refetch } = renderHook(() => {}, ['response'])

    act(() => {
      realtime.emit('data_changed', {
        event: 'data_changed', category: 'response', data: {}, timestamp: '',
      })
    })

    expect(refetch).not.toHaveBeenCalled()
    act(() => {
      vi.advanceTimersByTime(260)
    })
    expect(refetch).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('ignores non-matching categories', () => {
    vi.useFakeTimers()
    const { refetch } = renderHook(() => {}, ['response'])

    act(() => {
      realtime.emit('data_changed', {
        event: 'data_changed', category: 'interview', data: {}, timestamp: '',
      })
    })
    act(() => { vi.advanceTimersByTime(300) })
    expect(refetch).not.toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('refetches on every data_changed event when no categories are given', () => {
    vi.useFakeTimers()
    const { refetch } = renderHook(() => {})

    act(() => {
      realtime.emit('data_changed', {
        event: 'data_changed', category: 'anything', data: {}, timestamp: '',
      })
    })
    act(() => { vi.advanceTimersByTime(260) })
    expect(refetch).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('coalesces a burst of events into a single refetch', () => {
    vi.useFakeTimers()
    const { refetch } = renderHook(() => [], ['response'])

    act(() => {
      realtime.emit('data_changed', { event: 'data_changed', category: 'response', data: {}, timestamp: '' })
      realtime.emit('data_changed', { event: 'data_changed', category: 'response', data: {}, timestamp: '' })
      realtime.emit('data_changed', { event: 'data_changed', category: 'response', data: {}, timestamp: '' })
    })
    act(() => { vi.advanceTimersByTime(260) })
    expect(refetch).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})
