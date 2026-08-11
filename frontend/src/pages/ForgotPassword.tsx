import React, { useState } from 'react'
import { Form, Button, Card, Alert } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { FiMail, FiArrowLeft } from 'react-icons/fi'
import { api } from '../services/api'
import ErrorAlert from '../components/ui/ErrorAlert'

const ForgotPassword: React.FC = () => {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await api.auth.forgotPassword(email)
      setSent(true)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') || t('forgotPassword.failed') : detail || t('forgotPassword.failed'))
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
            <FiMail />
          </div>
          <h4 className="fw-bold mb-1">{t('forgotPassword.title')}</h4>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>{t('forgotPassword.subtitle')}</p>
        </div>

        <Card className="shadow-sm">
          <Card.Body className="p-4">
            {sent ? (
              <Alert variant="success" className="mb-0">
                {t('forgotPassword.sent')}
              </Alert>
            ) : (
              <>
                <ErrorAlert message={error} onClose={() => setError('')} />

                <Form onSubmit={handleSubmit}>
                  <Form.Group className="mb-4">
                    <Form.Label className="small fw-medium text-muted">{t('forgotPassword.email')}</Form.Label>
                    <div className="input-group">
                      <span className="input-group-text bg-light"><FiMail className="text-muted" /></span>
                      <Form.Control
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder={t('forgotPassword.emailPlaceholder')}
                        required
                        autoFocus
                      />
                    </div>
                  </Form.Group>

                  <Button variant="primary" type="submit" className="w-100 mb-3" disabled={loading}>
                    {loading ? t('forgotPassword.sending') : t('forgotPassword.sendResetLink')}
                  </Button>
                </Form>
              </>
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

export default ForgotPassword