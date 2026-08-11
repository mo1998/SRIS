import React from 'react'
import { Modal, Button } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'

interface ConfirmModalProps {
  show: boolean
  title: string
  message: string
  confirmLabel?: string
  confirmVariant?: string
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  show, title, message, confirmLabel,
  confirmVariant = 'danger', onConfirm, onCancel, loading
}) => {
  const { t } = useTranslation()
  const resolvedConfirmLabel = confirmLabel ?? t('common.confirm')

  return (
    <Modal show={show} onHide={onCancel} centered>
      <Modal.Header closeButton>
        <Modal.Title>{title}</Modal.Title>
      </Modal.Header>
      <Modal.Body>{message}</Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onCancel} disabled={loading}>{t('common.cancel')}</Button>
        <Button variant={confirmVariant} onClick={onConfirm} disabled={loading}>
          {loading ? t('common.processing') : resolvedConfirmLabel}
        </Button>
      </Modal.Footer>
    </Modal>
  )
}

export default ConfirmModal
