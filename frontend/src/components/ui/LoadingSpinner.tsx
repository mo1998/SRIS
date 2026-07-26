import React from 'react'
import { Spinner } from 'react-bootstrap'

interface LoadingSpinnerProps {
  text?: string
  size?: 'sm' | 'lg'
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ text = 'Loading...', size = 'lg' }) => (
  <div className="d-flex flex-column align-items-center justify-content-center py-5">
    <Spinner animation="border" variant="primary" size={size === 'lg' ? undefined : size} />
    <p className="text-muted mt-3 mb-0">{text}</p>
  </div>
)

export default LoadingSpinner
