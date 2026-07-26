import React from 'react'
import { Card } from 'react-bootstrap'

interface StatCardProps {
  icon: React.ReactNode
  label: string
  value: string | number
  variant?: string
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, variant }) => (
  <Card className="h-100">
    <Card.Body className="d-flex align-items-start gap-3 p-4">
      <div
        className="d-flex align-items-center justify-content-center rounded-3 flex-shrink-0"
        style={{
          width: 48, height: 48,
          background: variant ? `var(--color-${variant}-light, #eef2ff)` : 'var(--color-primary-light)',
          color: variant ? `var(--color-${variant}, #4f46e5)` : 'var(--color-primary)',
          fontSize: '1.25rem'
        }}
      >
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-muted fs-6 fw-medium mb-0" style={{ fontSize: '0.8rem' }}>{label}</p>
        <p className="fw-bold mb-0" style={{ fontSize: '1.75rem', lineHeight: 1.2 }}>{value}</p>
      </div>
    </Card.Body>
  </Card>
)

export default StatCard
