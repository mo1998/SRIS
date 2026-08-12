import React from 'react'
import { Button } from 'react-bootstrap'
import { FiRefreshCw } from 'react-icons/fi'
import { useTranslation } from 'react-i18next'

const UpdateBanner: React.FC = () => {
  const { t } = useTranslation()
  const [visible, setVisible] = React.useState(false)

  React.useEffect(() => {
    let stop: (() => void) | null = null
    let mounted = true

    import('../../lib/versionCheck').then(({ startVersionCheck }) => {
      if (!mounted) return
      stop = startVersionCheck(() => {
        if (mounted) setVisible(true)
      })
    })

    return () => {
      mounted = false
      stop?.()
    }
  }, [])

  if (!visible) return null

  return (
    <div
      className="d-flex align-items-center justify-content-center gap-3 px-3 py-2 text-white w-100"
      style={{ background: '#0d47a1', position: 'fixed', top: 0, zIndex: 10000 }}
    >
      <span>{t('updateBanner.message')}</span>
      <Button size="sm" variant="light" onClick={() => window.location.reload()}>
        <FiRefreshCw className="me-1" />
        {t('updateBanner.reload')}
      </Button>
      <button
        className="btn-close btn-close-white"
        aria-label={t('common.close')}
        onClick={() => setVisible(false)}
      />
    </div>
  )
}

export default UpdateBanner