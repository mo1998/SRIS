import React from 'react'
import { Spinner } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'

interface LoadingSpinnerProps {
  text?: string
  size?: 'sm' | 'lg'
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ text, size = 'lg' }) => {
  const { t } = useTranslation()
  const resolvedText = text ?? t('common.loading')

  return (
    <div className="d-flex flex-column align-items-center justify-content-center py-5">
      <Spinner animation="border" variant="primary" size={size === 'lg' ? undefined : size} />
      <p className="text-muted mt-3 mb-0">{resolvedText}</p>
    </div>
  )
}

export default LoadingSpinner
