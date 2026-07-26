import { useCallback } from 'react'
import { showToast } from '../components/ui/Toast'

export function useToast() {
  const success = useCallback((title: string, message?: string) => showToast('success', title, message), [])
  const error = useCallback((title: string, message?: string) => showToast('error', title, message), [])
  const warning = useCallback((title: string, message?: string) => showToast('warning', title, message), [])
  const info = useCallback((title: string, message?: string) => showToast('info', title, message), [])

  return { success, error, warning, info }
}
