import React, { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Form, Row } from 'react-bootstrap'
import { api } from '../services/api'
import { useAuth } from '../store/authStore'
import { FiLock, FiSave, FiUser } from 'react-icons/fi'
import PageHeader from '../components/ui/PageHeader'
import ErrorAlert from '../components/ui/ErrorAlert'
import { useToast } from '../hooks/useToast'

const AccountSettings: React.FC = () => {
  const { user, updateUser } = useAuth()
  const [fullName, setFullName] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [changingPassword, setChangingPassword] = useState(false)
  const toast = useToast()

  useEffect(() => {
    setFullName(user?.full_name || '')
    setPhone(user?.phone || '')
  }, [user])

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')
    setSaving(true)

    try {
      const response = await api.users.updateMe({
        full_name: fullName,
        phone: phone || undefined,
      })
      updateUser(response.data)
      toast.success('Account updated')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update account')
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setPasswordError('')

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
      toast.success('Password updated')
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || 'Failed to update password')
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <div>
      <PageHeader title="Account Settings" subtitle="Manage your profile and password" />
      <Row className="justify-content-center">
        <Col lg={7} xl={6}>
          <Card className="mb-4">
            <Card.Body>
              <ErrorAlert message={error} onClose={() => setError('')} />

              <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3" controlId="account-email">
                  <Form.Label className="small fw-medium text-muted">Email</Form.Label>
                  <Form.Control type="email" value={user?.email || ''} disabled />
                </Form.Group>

                <Form.Group className="mb-3" controlId="account-role">
                  <Form.Label className="small fw-medium text-muted">Role</Form.Label>
                  <Form.Control value={user?.role || ''} disabled />
                </Form.Group>

                <Form.Group className="mb-3" controlId="account-full-name">
                  <Form.Label className="small fw-medium text-muted">Full Name</Form.Label>
                  <Form.Control value={fullName} onChange={(e) => setFullName(e.target.value)} required />
                </Form.Group>

                <Form.Group className="mb-4" controlId="account-phone">
                  <Form.Label className="small fw-medium text-muted">Phone</Form.Label>
                  <Form.Control value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Optional" />
                </Form.Group>

                <Button type="submit" variant="primary" disabled={saving}>
                  <FiSave className="me-2" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </Form>
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Body>
              <h5 className="fw-semibold mb-3"><FiLock className="me-2" />Change Password</h5>
              <ErrorAlert message={passwordError} onClose={() => setPasswordError('')} />

              <Form onSubmit={handlePasswordSubmit}>
                <Form.Group className="mb-3" controlId="account-current-password">
                  <Form.Label className="small fw-medium text-muted">Current Password</Form.Label>
                  <Form.Control type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
                </Form.Group>

                <Form.Group className="mb-3" controlId="account-new-password">
                  <Form.Label className="small fw-medium text-muted">New Password</Form.Label>
                  <Form.Control type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} minLength={8} required />
                </Form.Group>

                <Form.Group className="mb-4" controlId="account-confirm-password">
                  <Form.Label className="small fw-medium text-muted">Confirm New Password</Form.Label>
                  <Form.Control type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} minLength={8} required />
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
    </div>
  )
}

export default AccountSettings