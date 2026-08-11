import React, { useState } from 'react'
import { Form, Button, Card, Alert } from 'react-bootstrap'
import { Link, useSearchParams } from 'react-router-dom'
import { FiLock, FiArrowLeft } from 'react-icons/fi'
import { api } from '../services/api'
import ErrorAlert from '../components/ui/ErrorAlert'

const ResetPassword: React.FC = () => {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await api.auth.resetPassword(token, password)
      setDone(true)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') || 'Reset failed' : detail || 'Reset failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
      <div style={{ maxWidth: 400, width: '100%' }}>
        <div className="text-center mb-4">
          <div className="d-inline-flex align-items-center justify-content-center rounded-3 mb-3"
            style={{ width: 56, height: 56, background: 'var(--color-primary-light)', color: 'var(--color-primary)', fontSize: '1.5rem' }}>
            <FiLock />
          </div>
          <h4 className="fw-bold mb-1">Set a new password</h4>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>Choose a strong password for your account</p>
        </div>

        <Card className="shadow-sm">
          <Card.Body className="p-4">
            {done ? (
              <Alert variant="success" className="mb-3">
                Your password has been reset. You can now sign in with your new password.
              </Alert>
            ) : token ? (
              <>
                <ErrorAlert message={error} onClose={() => setError('')} />

                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-3">
                    <Form.Label className="small fw-medium text-muted">New password</Form.Label>
                    <div className="input-group">
                      <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                      <Form.Control
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="At least 8 characters"
                        required
                        autoFocus
                      />
                    </div>
                  </Form.Group>

                  <Form.Group className="mb-4">
                    <Form.Label className="small fw-medium text-muted">Confirm new password</Form.Label>
                    <div className="input-group">
                      <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                      <Form.Control
                        type="password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        placeholder="Re-enter your new password"
                        required
                      />
                    </div>
                  </Form.Group>

                  <Button variant="primary" type="submit" className="w-100 mb-3" disabled={loading}>
                    {loading ? 'Resetting...' : 'Reset password'}
                  </Button>
                </Form>
              </>
            ) : (
              <Alert variant="danger" className="mb-3">Invalid or missing reset link.</Alert>
            )}

            <p className="text-center mb-0" style={{ fontSize: '0.875rem' }}>
              <Link to="/login" className="fw-medium"><FiArrowLeft className="me-1" />Back to sign in</Link>
            </p>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default ResetPassword