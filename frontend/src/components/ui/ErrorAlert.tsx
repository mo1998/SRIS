import React from 'react'
import { Alert } from 'react-bootstrap'

interface ErrorAlertProps {
  message: string
  onClose?: () => void
}

const ErrorAlert: React.FC<ErrorAlertProps> = ({ message, onClose }) => {
  if (!message) return null
  return (
    <Alert variant="danger" dismissible={!!onClose} onClose={onClose} className="mb-3">
      {message}
    </Alert>
  )
}

export default ErrorAlert
