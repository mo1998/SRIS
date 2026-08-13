import { useEffect, useRef } from 'react'
import { realtime, type DataChangedEvent } from '../services/realtime'

const DEBOUNCE_MS = 250

/**
 * Subscribes `refetch` to realtime `data_changed` events so the component's data
 * refreshes automatically when any relevant system action happens elsewhere.
 *
 * Pass `categories` to limit refetches to specific event categories (e.g.
 * `['notification']`). Omit it to refetch on every data-change event.
 */
export function useRealTimeRefresh(
  refetch: () => void | Promise<void>,
  categories?: string[],
) {
  const refetchRef = useRef(refetch)
  useEffect(() => {
    refetchRef.current = refetch
  }, [refetch])

  const categoriesKey = categories?.slice().sort().join(',') ?? ''

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null
    const fire = (msg: DataChangedEvent) => {
      if (categories && msg.category && !categories.includes(msg.category)) {
        return
      }
      if (timer) clearTimeout(timer)
      timer = setTimeout(() => {
        const fn = refetchRef.current
        fn()
      }, DEBOUNCE_MS)
    }

    realtime.on('data_changed', fire)
    return () => {
      realtime.off('data_changed', fire)
      if (timer) clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoriesKey])
}
