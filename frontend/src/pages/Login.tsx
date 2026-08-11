import React, { useState } from 'react'
import { Form, Button, Card, Alert } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../store/authStore'
import { Link, useNavigate } from 'react-router-dom'
import { FiLogIn, FiMail, FiLock } from 'react-icons/fi'
import ErrorAlert from '../components/ui/ErrorAlert'

const Login: React.FC = () => {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      await login(email, password)
      navigate('/')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join('; ') || t('login.failed'))
      } else {
        setError(detail || t('login.failed'))
      }
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
            <FiLogIn />
          </div>
          <h4 className="fw-bold mb-1">{t('login.welcomeBack')}</h4>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>{t('login.subtitle')}</p>
        </div>
        
        <Card className="shadow-sm">
          <Card.Body className="p-4">
            <ErrorAlert message={error} onClose={() => setError('')} />
            
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">{t('login.email')}</Form.Label>
                <div className="input-group">
                  <span className="input-group-text bg-light"><FiMail className="text-muted" /></span>
                  <Form.Control
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={t('login.emailPlaceholder')}
                    required
                  />
                </div>
              </Form.Group>
              
              <Form.Group className="mb-4">
                <Form.Label className="small fw-medium text-muted">{t('login.password')}</Form.Label>
                <div className="input-group">
                  <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                  <Form.Control
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={t('login.passwordPlaceholder')}
                    required
                  />
                </div>
              </Form.Group>
              
              <Button variant="primary" type="submit" className="w-100 mb-2" disabled={loading}>
                {loading ? t('login.signingIn') : t('login.signIn')}
              </Button>
            </Form>

            <div className="text-center mb-3">
              <Link to="/forgot-password" className="small fw-medium" style={{ fontSize: '0.875rem' }}>{t('login.forgotPassword')}</Link>
            </div>

            <p className="text-center mb-0" style={{ fontSize: '0.875rem' }}>
              {t('login.noAccount')} <Link to="/register" className="fw-medium">{t('login.register')}</Link>
            </p>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default Login
