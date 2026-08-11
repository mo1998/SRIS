import React, { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Form, Row } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { useAuth } from '../store/authStore'
import { FiLock, FiSave, FiUser } from 'react-icons/fi'
import PageHeader from '../components/ui/PageHeader'
import ErrorAlert from '../components/ui/ErrorAlert'
import { useToast } from '../hooks/useToast'

const AccountSettings: React.FC = () => {
  const { t } = useTranslation()
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
      toast.success(t('account.updated'))
    } catch (err: any) {
      setError(err.response?.data?.detail || t('account.updateFailed'))
    } finally {
      setSaving(false)
    }
  }

  const handlePasswordSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setPasswordError('')

    if (newPassword !== confirmPassword) {
      setPasswordError(t('account.passwordsDoNotMatch'))
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
      toast.success(t('account.passwordUpdated'))
    } catch (err: any) {
      setPasswordError(err.response?.data?.detail || t('account.passwordFailed'))
    } finally {
      setChangingPassword(false)
    }
  }

  return (
    <div>
      <PageHeader title={t('account.title')} subtitle={t('account.subtitle')} />
      <Row className="justify-content-center">
        <Col lg={7} xl={6}>
          <Card className="mb-4">
            <Card.Body>
              <ErrorAlert message={error} onClose={() => setError('')} />

              <Form onSubmit={handleSubmit}>
                <Form.Group className="mb-3" controlId="account-email">
                  <Form.Label className="small fw-medium text-muted">{t('account.email')}</Form.Label>
                  <Form.Control type="email" value={user?.email || ''} disabled />
                </Form.Group>

                <Form.Group className="mb-3" controlId="account-role">
                  <Form.Label className="small fw-medium text-muted">{t('account.role')}</Form.Label>
                  <Form.Control value={user?.role || ''} disabled />
                </Form.Group>

                <Form.Group className="mb-3" controlId="account-full-name">
                  <Form.Label className="small fw-medium text-muted">{t('account.fullName')}</Form.Label>
                  <Form.Control value={fullName} onChange={(e) => setFullName(e.target.value)} required />
                </Form.Group>

                <Form.Group className="mb-4" controlId="account-phone">
                  <Form.Label className="small fw-medium text-muted">{t('account.phone')}</Form.Label>
                  <Form.Control value={phone} onChange={(e) => setPhone(e.target.value)} placeholder={t('account.phoneOptional')} />
                </Form.Group>

                <Button type="submit" variant="primary" disabled={saving}>
                  <FiSave className="me-2" />
                  {saving ? t('account.saving') : t('account.saveChanges')}
                </Button>
              </Form>
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Body>
              <h5 className="fw-semibold mb-3"><FiLock className="me-2" />{t('account.changePassword')}</h5>
              <ErrorAlert message={passwordError} onClose={() => setPasswordError('')} />

              <Form onSubmit={handlePasswordSubmit}>
                <Form.Group className="mb-3" controlId="account-current-password">
                  <Form.Label className="small fw-medium text-muted">{t('account.currentPassword')}</Form.Label>
                  <Form.Control type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} required />
                </Form.Group>

                <Form.Group className="mb-3" controlId="account-new-password">
                  <Form.Label className="small fw-medium text-muted">{t('account.newPassword')}</Form.Label>
                  <Form.Control type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} minLength={8} required />
                </Form.Group>

                <Form.Group className="mb-4" controlId="account-confirm-password">
                  <Form.Label className="small fw-medium text-muted">{t('account.confirmNewPassword')}</Form.Label>
                  <Form.Control type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} minLength={8} required />
                </Form.Group>

                <Button type="submit" variant="outline-primary" disabled={changingPassword}>
                  <FiLock className="me-2" />
                  {changingPassword ? t('account.updating') : t('account.updatePassword')}
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