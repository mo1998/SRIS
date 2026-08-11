import React, { useState } from 'react'
import { Form, Button, Card, Row, Col } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../store/authStore'
import { Link, useNavigate } from 'react-router-dom'
import { FiUserPlus, FiMail, FiLock, FiUser, FiBriefcase } from 'react-icons/fi'
import ErrorAlert from '../components/ui/ErrorAlert'

type RegisterRole = 'employer' | 'employee'

const Register: React.FC = () => {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    role: 'employee' as RegisterRole,
    company_name: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (formData.password !== formData.confirmPassword) {
      setError(t('register.passwordsDoNotMatch'))
      return
    }
    
    if (formData.password.length < 8) {
      setError(t('register.passwordTooShort'))
      return
    }
    
    if (!/[a-z]/.test(formData.password)) {
      setError(t('register.passwordLowercase'))
      return
    }
    if (!/[A-Z]/.test(formData.password)) {
      setError(t('register.passwordUppercase'))
      return
    }
    if (!/[0-9]/.test(formData.password)) {
      setError(t('register.passwordNumber'))
      return
    }
    
    setLoading(true)
    
    try {
      const { confirmPassword, ...registerData } = formData
      await register(registerData)
      navigate('/')
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg).join('; ') || t('register.failed'))
      } else {
        setError(detail || t('register.failed'))
      }
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
      <div style={{ maxWidth: 480, width: '100%' }}>
        <div className="text-center mb-4">
          <div className="d-inline-flex align-items-center justify-content-center rounded-3 mb-3"
            style={{ width: 56, height: 56, background: 'var(--color-primary-light)', color: 'var(--color-primary)', fontSize: '1.5rem' }}>
            <FiUserPlus />
          </div>
          <h4 className="fw-bold mb-1">{t('register.title')}</h4>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>{t('register.subtitle')}</p>
        </div>
        
        <Card className="shadow-sm">
          <Card.Body className="p-4">
            <ErrorAlert message={error} onClose={() => setError('')} />
            
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">{t('register.fullName')}</Form.Label>
                <div className="input-group">
                  <span className="input-group-text bg-light"><FiUser className="text-muted" /></span>
                  <Form.Control type="text" value={formData.full_name}
                    onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                    placeholder={t('register.fullNamePlaceholder')} required />
                </div>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">{t('register.email')}</Form.Label>
                <div className="input-group">
                  <span className="input-group-text bg-light"><FiMail className="text-muted" /></span>
                  <Form.Control type="email" value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    placeholder={t('register.emailPlaceholder')} required />
                </div>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">{t('register.role')}</Form.Label>
                <Form.Select value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value as RegisterRole})}>
                  <option value="employee">{t('register.roleEmployee')}</option>
                  <option value="employer">{t('register.roleEmployer')}</option>
                </Form.Select>
              </Form.Group>
              
              {formData.role === 'employer' && (
                <Form.Group className="mb-3">
                  <Form.Label className="small fw-medium text-muted">{t('register.companyName')}</Form.Label>
                  <div className="input-group">
                    <span className="input-group-text bg-light"><FiBriefcase className="text-muted" /></span>
                    <Form.Control type="text" value={formData.company_name}
                      onChange={(e) => setFormData({...formData, company_name: e.target.value})}
                      placeholder={t('register.companyNamePlaceholder')} required />
                  </div>
                </Form.Group>
              )}
              
              <Row className="g-2 mb-3">
                <Col xs={6}>
                  <Form.Label className="small fw-medium text-muted">{t('register.password')}</Form.Label>
                  <div className="input-group">
                    <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                    <Form.Control type="password" value={formData.password}
                      onChange={(e) => setFormData({...formData, password: e.target.value})}
                      placeholder={t('register.passwordPlaceholder')} required />
                  </div>
                </Col>
                <Col xs={6}>
                  <Form.Label className="small fw-medium text-muted">{t('register.confirmPassword')}</Form.Label>
                  <Form.Control type="password" value={formData.confirmPassword}
                    onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                    placeholder={t('register.repeatPassword')} required />
                </Col>
              </Row>
              
              <Button variant="primary" type="submit" className="w-100 mb-3" disabled={loading}>
                {loading ? t('register.creating') : t('register.title')}
              </Button>
            </Form>
            
            <p className="text-center mb-0" style={{ fontSize: '0.875rem' }}>
              {t('register.alreadyHaveAccount')} <Link to="/login" className="fw-medium">{t('register.signIn')}</Link>
            </p>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default Register
