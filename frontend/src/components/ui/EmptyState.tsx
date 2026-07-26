import React from 'react'
import { Button } from 'react-bootstrap'
import { FiInbox } from 'react-icons/fi'

interface EmptyStateProps {
  icon?: React.ReactNode
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
}

const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description, actionLabel, onAction }) => (
  <div className="text-center py-5">
    <div className="text-muted mb-3" style={{ fontSize: '2.5rem' }}>
      {icon || <FiInbox />}
    </div>
    <h5 className="text-muted mb-2">{title}</h5>
    {description && <p className="text-muted mb-3" style={{ maxWidth: 400, margin: '0 auto' }}>{description}</p>}
    {actionLabel && onAction && (
      <Button variant="primary" onClick={onAction}>{actionLabel}</Button>
    )}
  </div>
)

export default EmptyState
