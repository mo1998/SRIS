import React, { useState } from 'react'
import { Form, Button, Card, Alert } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { FiLock, FiArrowLeft } from 'react-icons/fi'
import { api } from '../services/api'
import ErrorAlert from '../components/ui/ErrorAlert'

const ResetPassword: React.FC = () => {
  const { t } = useTranslation()
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
      setError(t('resetPassword.passwordsDoNotMatch'))
      return
    }

    setLoading(true)
    try {
      await api.auth.resetPassword(token, password)
      setDone(true)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') || t('resetPassword.failed') : detail || t('resetPassword.failed'))
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
          <h4 className="fw-bold mb-1">{t('resetPassword.title')}</h4>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>{t('resetPassword.subtitle')}</p>
        </div>

        <Card className="shadow-sm">
          <Card.Body className="p-4">
            {done ? (
              <Alert variant="success" className="mb-3">
                {t('resetPassword.done')}
              </Alert>
            ) : token ? (
              <>
                <ErrorAlert message={error} onClose={() => setError('')} />

                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-3">
                    <Form.Label className="small fw-medium text-muted">{t('resetPassword.newPassword')}</Form.Label>
                    <div className="input-group">
                      <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                      <Form.Control
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder={t('resetPassword.newPasswordPlaceholder')}
                        required
                        autoFocus
                      />
                    </div>
                  </Form.Group>

                  <Form.Group className="mb-4">
                    <Form.Label className="small fw-medium text-muted">{t('resetPassword.confirmNewPassword')}</Form.Label>
                    <div className="input-group">
                      <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                      <Form.Control
                        type="password"
                        value={confirm}
                        onChange={(e) => setConfirm(e.target.value)}
                        placeholder={t('resetPassword.confirmPlaceholder')}
                        required
                      />
                    </div>
                  </Form.Group>

                  <Button variant="primary" type="submit" className="w-100 mb-3" disabled={loading}>
                    {loading ? t('resetPassword.resetting') : t('resetPassword.resetPassword')}
                  </Button>
                </Form>
              </>
            ) : (
              <Alert variant="danger" className="mb-3">{t('resetPassword.invalidLink')}</Alert>
            )}

            <p className="text-center mb-0" style={{ fontSize: '0.875rem' }}>
              <Link to="/login" className="fw-medium"><FiArrowLeft className="me-1" />{t('forgotPassword.backToSignIn')}</Link>
            </p>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default ResetPassword