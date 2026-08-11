import React, { useEffect, useRef, useState } from 'react'
import { FiBell } from 'react-icons/fi'
import { api } from '../services/api'

interface NotificationItem {
  id: number
  type: string
  title: string
  message?: string
  link?: string
  is_read: boolean
  created_at: string
}

const timeAgo = (iso: string): string => {
  const then = new Date(iso).getTime()
  const seconds = Math.floor((Date.now() - then) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

const NotificationBell: React.FC = () => {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [error, setError] = useState('')
  const containerRef = useRef<HTMLDivElement>(null)

  const load = async () => {
    try {
      const res = await api.notifications.list(20)
      setNotifications(res.data.notifications || [])
      setUnreadCount(res.data.unread_count || 0)
    } catch (err: any) {
      setError(err.response?.status === 401 ? '' : 'Failed to load notifications')
    }
  }

  const refreshUnread = async () => {
    try {
      const res = await api.notifications.unreadCount()
      setUnreadCount(res.data.unread_count || 0)
    } catch { /* silent */ }
  }

  useEffect(() => {
    load()
    const poll = window.setInterval(refreshUnread, 30000)
    return () => window.clearInterval(poll)
  }, [])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleMarkAll = async () => {
    try {
      await api.notifications.markAllRead()
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch { /* silent */ }
  }

  const handleOpenNotification = async (n: NotificationItem) => {
    if (!n.is_read) {
      try {
        await api.notifications.markRead(n.id)
        setNotifications((prev) => prev.map((p) => (p.id === n.id ? { ...p, is_read: true } : p)))
        setUnreadCount((c) => Math.max(0, c - 1))
      } catch { /* silent */ }
    }
    setOpen(false)
  }

  return (
    <div ref={containerRef} style={{ position: 'relative' }}>
      <button
        className="btn btn-link text-muted p-1"
        style={{ fontSize: '1.25rem', position: 'relative' }}
        onClick={() => { setOpen(!open); if (!open) load() }}
        aria-label="Notifications"
      >
        <FiBell />
        {unreadCount > 0 && (
          <span
            style={{
              position: 'absolute',
              top: -2,
              right: -2,
              background: 'var(--color-danger)',
              color: 'white',
              borderRadius: '50%',
              fontSize: '0.65rem',
              minWidth: 16,
              height: 16,
              lineHeight: '16px',
              textAlign: 'center',
              padding: '0 3px',
            }}
          >
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            right: '0.25rem',
            marginTop: '0.5rem',
            background: 'var(--color-white)',
            border: '1px solid var(--color-gray-200)',
            borderRadius: 'var(--radius-md)',
            boxShadow: 'var(--shadow-lg)',
            width: 340,
            maxHeight: 420,
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <div className="d-flex align-items-center justify-content-between px-3 py-2 border-bottom">
            <strong style={{ fontSize: '0.875rem' }}>Notifications</strong>
            {unreadCount > 0 && (
              <button className="btn btn-link btn-sm p-0 text-decoration-none" onClick={handleMarkAll}>
                Mark all read
              </button>
            )}
          </div>

          <div style={{ overflowY: 'auto', flex: 1 }}>
            {error && <div className="px-3 py-2 text-danger" style={{ fontSize: '0.8rem' }}>{error}</div>}
            {notifications.length === 0 && (
              <div className="px-3 py-4 text-center text-muted" style={{ fontSize: '0.85rem' }}>
                No notifications yet
              </div>
            )}
            {notifications.map((n) => (
              <button
                key={n.id}
                className="dropdown-item"
                onClick={() => handleOpenNotification(n)}
                style={{
                  whiteSpace: 'normal',
                  padding: '0.6rem 1rem',
                  background: n.is_read ? 'transparent' : 'var(--color-primary-50, #f0f4ff)',
                  borderRadius: 0,
                  borderBottom: '1px solid var(--color-gray-100)',
                }}
              >
                <div className="d-flex justify-content-between gap-2">
                  <strong style={{ fontSize: '0.8rem' }}>{n.title}</strong>
                  <small className="text-muted text-nowrap" style={{ fontSize: '0.7rem' }}>{timeAgo(n.created_at)}</small>
                </div>
                {n.message && (
                  <div className="text-muted" style={{ fontSize: '0.78rem', marginTop: '0.15rem' }}>{n.message}</div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificationBell