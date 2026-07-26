import React from 'react'
import { Modal, Button } from 'react-bootstrap'

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
  show, title, message, confirmLabel = 'Confirm',
  confirmVariant = 'danger', onConfirm, onCancel, loading
}) => (
  <Modal show={show} onHide={onCancel} centered>
    <Modal.Header closeButton>
      <Modal.Title>{title}</Modal.Title>
    </Modal.Header>
    <Modal.Body>{message}</Modal.Body>
    <Modal.Footer>
      <Button variant="secondary" onClick={onCancel} disabled={loading}>Cancel</Button>
      <Button variant={confirmVariant} onClick={onConfirm} disabled={loading}>
        {loading ? 'Processing...' : confirmLabel}
      </Button>
    </Modal.Footer>
  </Modal>
)

export default ConfirmModal
