import React, { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Form, Row } from 'react-bootstrap'
import { api } from '../services/api'
import { useAuth } from '../store/authStore'
import { FiLock, FiSave, FiUser } from 'react-icons/fi'

const AccountSettings: React.FC = () => {
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [passwordMessage, setPasswordMessage] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)

  useEffect(() => {
    setFullName(user?.full_name || '')
    setPhone(user?.phone || '')
  }, [user])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setSaving(true)

    try {
      const response = await api.users.updateMe({
        full_name: fullName,
        phone: phone || undefined,
      })
      updateUser(response.data)
      setMessage('Account updated')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update account')
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setPasswordError('')
    setPasswordMessage('')

    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }

    setChangingPassword(true)

    try {
      await api.users.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordMessage('Password updated')
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed to update password')
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <Row className="justify-content-center">
      <Col lg={7} xl={6}>
        <Card className="mb-4">
          <Card.Header>
            <h1 className="h4 mb-0">
              <FiUser className="me-2" />
              Account Settings
            </h1>
          </Card.Header>
          <Card.Body>
            {error && <Alert variant="danger">{error}</Alert>}
            {message && <Alert variant="success">{message}</Alert>}

            <Form onSubmit={handleSubmit}>
              <Form.Group className="mb-3" controlId="account-email">
                <Form.Label>Email</Form.Label>
                <Form.Control type="email" value={user?.email || ''} disabled />
              </Form.Group>

              <Form.Group className="mb-3" controlId="account-role">
                <Form.Label>Role</Form.Label>
                <Form.Control value={user?.role || ''} disabled />
              </Form.Group>

              <Form.Group className="mb-3" controlId="account-full-name">
                <Form.Label>Full Name</Form.Label>
                <Form.Control
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  required
                />
              </Form.Group>

              <Form.Group className="mb-4" controlId="account-phone">
                <Form.Label>Phone</Form.Label>
                <Form.Control
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                  placeholder="Optional"
                />
              </Form.Group>

              <Button type="submit" disabled={saving}>
                <FiSave className="me-2" />
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </Form>
          </Card.Body>
        </Card>

        <Card>
          <Card.Header>
            <h2 className="h5 mb-0">
              <FiLock className="me-2" />
              Change Password
            </h2>
          </Card.Header>
          <Card.Body>
            {passwordError && <Alert variant="danger">{passwordError}</Alert>}
            {passwordMessage && <Alert variant="success">{passwordMessage}</Alert>}

            <Form onSubmit={handlePasswordSubmit}>
              <Form.Group className="mb-3" controlId="account-current-password">
                <Form.Label>Current Password</Form.Label>
                <Form.Control
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                />
              </Form.Group>

              <Form.Group className="mb-3" controlId="account-new-password">
                <Form.Label>New Password</Form.Label>
                <Form.Control
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  minLength={8}
                  required
                />
              </Form.Group>

              <Form.Group className="mb-4" controlId="account-confirm-password">
                <Form.Label>Confirm New Password</Form.Label>
                <Form.Control
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  minLength={8}
                  required
                />
              </Form.Group>

              <Button type="submit" variant="outline-primary" disabled={changingPassword}>
                <FiLock className="me-2" />
                {changingPassword ? 'Updating...' : 'Update Password'}
              </Button>
            </Form>
          </Card.Body>
        </Card>
      </Col>
    </Row>
  )
}

export default AccountSettings