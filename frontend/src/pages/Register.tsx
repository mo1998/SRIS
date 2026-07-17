import React, { useState } from 'react'
import { Form, Button, Card, Alert, Container } from 'react-bootstrap'
import { useAuth } from '../store/authStore'
import { Link, useNavigate } from 'react-router-dom'
import { FiUserPlus } from 'react-icons/fi'

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
    
    setLoading(true)
    
    try {
      const { confirmPassword, ...registerData } = formData
      await register(registerData)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <Container className="d-flex justify-content-center align-items-center" style={{ minHeight: '80vh' }}>
      <Card style={{ maxWidth: '500px', width: '100%' }}>
        <Card.Body>
          <Card.Title className="text-center mb-4">
            <FiUserPlus className="me-2" />
            Create Account
          </Card.Title>
          
          {error && <Alert variant="danger">{error}</Alert>}
          
          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3">
              <Form.Label>Full Name</Form.Label>
              <Form.Control
                type="text"
                value={formData.full_name}
                onChange={(e) => setFormData({...formData, full_name: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Email</Form.Label>
              <Form.Control
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Role</Form.Label>
              <Form.Select
                value={formData.role}
                onChange={(e) => setFormData({...formData, role: e.target.value as RegisterRole})}
              >
                <option value="employee">Employee/Candidate</option>
                <option value="employer">Employer</option>
              </Form.Select>
            </Form.Group>
            
            {formData.role === 'employer' && (
              <Form.Group className="mb-3">
                <Form.Label>Company Name</Form.Label>
                <Form.Control
                  type="text"
                  value={formData.company_name}
                  onChange={(e) => setFormData({...formData, company_name: e.target.value})}
                  required
                />
              </Form.Group>
            )}
            
            <Form.Group className="mb-3">
              <Form.Label>Password</Form.Label>
              <Form.Control
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({...formData, password: e.target.value})}
                required
              />
            </Form.Group>
            
            <Form.Group className="mb-3">
              <Form.Label>Confirm Password</Form.Label>
              <Form.Control
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({...formData, confirmPassword: e.target.value})}
                required
              />
            </Form.Group>
            
            <Button variant="primary" type="submit" className="w-100" disabled={loading}>
              {loading ? 'Creating account...' : 'Register'}
            </Button>
          </Form>
          
          <div className="text-center mt-3">
            Already have an account? <Link to="/login">Login</Link>
          </div>
        </Card.Body>
      </Card>
    </Container>
  )
}

export default Register
