import React, { useEffect, useCallback } from 'react'
import { Toast as BsToast, ToastContainer as BsToastContainer } from 'react-bootstrap'
import { FiCheckCircle, FiAlertCircle, FiAlertTriangle, FiInfo, FiX } from 'react-icons/fi'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastMessage {
  id: string
  type: ToastType
  title: string
  message?: string
}

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <FiCheckCircle />,
  error: <FiAlertCircle />,
  warning: <FiAlertTriangle />,
  info: <FiInfo />,
}

const BG_COLORS: Record<ToastType, string> = {
  success: '#10b981',
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',
}

let toastListeners: ((toast: ToastMessage) => void)[] = []

export const showToast = (type: ToastType, title: string, message?: string) => {
  const id = Date.now().toString() + Math.random().toString(36).slice(2)
  toastListeners.forEach(fn => fn({ id, type, title, message }))
}

const SingleToast: React.FC<{ toast: ToastMessage; onRemove: (id: string) => void }> = ({ toast, onRemove }) => {
  useEffect(() => {
    const timer = setTimeout(() => onRemove(toast.id), 5000)
    return () => clearTimeout(timer)
  }, [toast.id, onRemove])

  return (
    <BsToast onClose={() => onRemove(toast.id)} className="border-0 text-white" style={{ background: BG_COLORS[toast.type] }}>
      <div className="d-flex align-items-start p-2">
        <div className="me-2 mt-1">{ICONS[toast.type]}</div>
        <div className="flex-grow-1">
          <strong>{toast.title}</strong>
          {toast.message && <div className="small mt-1">{toast.message}</div>}
        </div>
        <button className="btn-close btn-close-white ms-2" onClick={() => onRemove(toast.id)} aria-label="Close" />
      </div>
    </BsToast>
  )
}

export const ToastContainer: React.FC = () => {
  const [toasts, setToasts] = React.useState<ToastMessage[]>([])

  const addToast = useCallback((toast: ToastMessage) => {
    setToasts(prev => [...prev, toast])
  }, [])

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  useEffect(() => {
    toastListeners.push(addToast)
    return () => { toastListeners = toastListeners.filter(fn => fn !== addToast) }
  }, [addToast])

  return (
    <BsToastContainer position="top-end" className="p-3" style={{ zIndex: 9999 }}>
      {toasts.map(t => (
        <SingleToast key={t.id} toast={t} onRemove={removeToast} />
      ))}
    </BsToastContainer>
  )
}
