import React from 'react'
import { useWebSocket } from '../hooks/useWebSocket'

/**
 * Mounts a single WebSocket connection for the whole app. The underlying hook
 * only connects once `useAuth` reports an authenticated session (with a token)
 * and reconnects automatically on token refresh/logout.
 */
export const RealTimeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  useWebSocket()
  return <>{children}</>
}
