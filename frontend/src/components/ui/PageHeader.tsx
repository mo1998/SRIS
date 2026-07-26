import React from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

const PageHeader: React.FC<PageHeaderProps> = ({ title, subtitle, actions }) => (
  <div className="d-flex justify-content-between align-items-start mb-4">
    <div>
      <h3 className="fw-bold mb-1" style={{ color: 'var(--color-dark)' }}>{title}</h3>
      {subtitle && <p className="text-muted mb-0">{subtitle}</p>}
    </div>
    {actions && <div className="d-flex gap-2 flex-shrink-0">{actions}</div>}
  </div>
)

export default PageHeader
