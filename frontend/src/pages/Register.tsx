import React, { useState } from 'react'
import { Form, Button, Card, Row, Col } from 'react-bootstrap'
import { useAuth } from '../store/authStore'
import { Link, useNavigate } from 'react-router-dom'
import { FiUserPlus, FiMail, FiLock, FiUser, FiBriefcase } from 'react-icons/fi'
import ErrorAlert from '../components/ui/ErrorAlert'

type RegisterRole = 'employer' | 'employee'

const Register: React.FC = () => {
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
      setError('Passwords do not match')
      return
    }
    
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    
    if (!/[a-z]/.test(formData.password)) {
      setError('Password must include a lowercase letter')
      return
    }
    if (!/[A-Z]/.test(formData.password)) {
      setError('Password must include an uppercase letter')
      return
    }
    if (!/[0-9]/.test(formData.password)) {
      setError('Password must include a number')
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
        setError(detail.map((d: any) => d.msg).join('; ') || 'Registration failed')
      } else {
        setError(detail || 'Registration failed')
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
          <h4 className="fw-bold mb-1">Create account</h4>
          <p className="text-muted mb-0" style={{ fontSize: '0.875rem' }}>Get started with SRIS</p>
        </div>
        
        <Card className="shadow-sm">
          <Card.Body className="p-4">
            <ErrorAlert message={error} onClose={() => setError('')} />
            
            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">Full Name</Form.Label>
                <div className="input-group">
                  <span className="input-group-text bg-light"><FiUser className="text-muted" /></span>
                  <Form.Control type="text" value={formData.full_name}
                    onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                    placeholder="John Doe" required />
                </div>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">Email</Form.Label>
                <div className="input-group">
                  <span className="input-group-text bg-light"><FiMail className="text-muted" /></span>
                  <Form.Control type="email" value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    placeholder="you@example.com" required />
                </div>
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label className="small fw-medium text-muted">Role</Form.Label>
                <Form.Select value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value as RegisterRole})}>
                  <option value="employee">Employee / Candidate</option>
                  <option value="employer">Employer</option>
                </Form.Select>
              </Form.Group>
              
              {formData.role === 'employer' && (
                <Form.Group className="mb-3">
                  <Form.Label className="small fw-medium text-muted">Company Name</Form.Label>
                  <div className="input-group">
                    <span className="input-group-text bg-light"><FiBriefcase className="text-muted" /></span>
                    <Form.Control type="text" value={formData.company_name}
                      onChange={(e) => setFormData({...formData, company_name: e.target.value})}
                      placeholder="Acme Inc." required />
                  </div>
                </Form.Group>
              )}
              
              <Row className="g-2 mb-3">
                <Col xs={6}>
                  <Form.Label className="small fw-medium text-muted">Password</Form.Label>
                  <div className="input-group">
                    <span className="input-group-text bg-light"><FiLock className="text-muted" /></span>
                    <Form.Control type="password" value={formData.password}
                      onChange={(e) => setFormData({...formData, password: e.target.value})}
                      placeholder="Min. 8 chars" required />
                  </div>
                </Col>
                <Col xs={6}>
                  <Form.Label className="small fw-medium text-muted">Confirm Password</Form.Label>
                  <Form.Control type="password" value={formData.confirmPassword}
                    onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                    placeholder="Repeat password" required />
                </Col>
              </Row>
              
              <Button variant="primary" type="submit" className="w-100 mb-3" disabled={loading}>
                {loading ? 'Creating account...' : 'Create account'}
              </Button>
            </Form>
            
            <p className="text-center mb-0" style={{ fontSize: '0.875rem' }}>
              Already have an account? <Link to="/login" className="fw-medium">Sign in</Link>
            </p>
          </Card.Body>
        </Card>
      </div>
    </div>
  )
}

export default Register
