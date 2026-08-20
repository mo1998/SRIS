import React, { useEffect, useState } from 'react'
import { Badge, Button, Card, Form, Row, Col, Table, Tabs, Tab } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { FiUserPlus, FiBriefcase, FiUsers } from 'react-icons/fi'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import ErrorAlert from '../components/ui/ErrorAlert'
import { useToast } from '../hooks/useToast'

const OrganizationSettings: React.FC = () => {
  const { t } = useTranslation()
  const toast = useToast()
  const [organization, setOrganization] = useState<any>(null)
  const [members, setMembers] = useState<any[]>([])
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState('reviewer')
  const [teamError, setTeamError] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    const [organizationResponse, membersResponse] = await Promise.all([
      api.users.getMyOrganization(),
      api.users.getOrganizationMembers(),
    ])
    setOrganization(organizationResponse.data)
    setMembers(membersResponse.data)
  }

  useEffect(() => {
    load().catch(() => toast.error(t('dashboard.loadFailed'), t('dashboard.loadError'))).finally(() => setLoading(false))
  }, [])

  const handleAddMember = async (event: React.FormEvent) => {
    event.preventDefault()
    setTeamError('')
    setAddingMember(true)
    try {
      await api.users.addMembership({ email: memberEmail, role: memberRole })
      setMemberEmail('')
      setMemberRole('reviewer')
      const membersResponse = await api.users.getOrganizationMembers()
      setMembers(membersResponse.data)
      toast.success(t('dashboard.memberAdded'))
    } catch (err: any) {
      setTeamError(err.response?.data?.detail || t('dashboard.memberAddFailed'))
    } finally {
      setAddingMember(false)
    }
  }

  if (loading) return <LoadingSpinner text={t('dashboard.loading')} />

  return (
    <div>
      <PageHeader title={t('dashboard.orgSettingsTitle')} subtitle={t('dashboard.orgSettingsSubtitle')} />

      <Card>
        <Card.Body>
          <Tabs defaultActiveKey="organization">
            <Tab
              eventKey="organization"
              title={<span className="d-inline-flex align-items-center gap-2"><FiBriefcase />{t('dashboard.organization')}</span>}
            >
              <div className="pt-3">
                {organization ? (
                  <>
                    <h4 className="fw-bold">{organization.name}</h4>
                    <p className="text-muted mb-0">{t('dashboard.teamMembersCount', { count: members.length })}</p>
                  </>
                ) : (
                  <p className="text-muted mb-0">{t('dashboard.noOrganization')}</p>
                )}
              </div>
            </Tab>

            <Tab
              eventKey="team"
              title={<span className="d-inline-flex align-items-center gap-2"><FiUsers />{t('dashboard.teamAccess')}</span>}
            >
              <div className="pt-3">
                <ErrorAlert message={teamError} onClose={() => setTeamError('')} />

                <Form onSubmit={handleAddMember} className="mb-3">
                  <Row className="g-2 align-items-end">
                    <Col md={6}>
                      <Form.Label className="small text-muted">{t('common.email')}</Form.Label>
                      <Form.Control type="email" value={memberEmail} onChange={(e) => setMemberEmail(e.target.value)}
                        placeholder={t('dashboard.addMemberPlaceholder')} required size="sm" />
                    </Col>
                    <Col md={4}>
                      <Form.Label className="small text-muted">{t('common.role')}</Form.Label>
                      <Form.Select value={memberRole} onChange={(e) => setMemberRole(e.target.value)} size="sm">
                        <option value="reviewer">{t('dashboard.reviewer')}</option>
                        <option value="recruiter">{t('dashboard.recruiter')}</option>
                        <option value="admin">{t('dashboard.admin')}</option>
                      </Form.Select>
                    </Col>
                    <Col md={2}>
                      <Button type="submit" variant="outline-primary" className="w-100" disabled={addingMember} size="sm">
                        <FiUserPlus className="me-1" /> {t('dashboard.add')}
                      </Button>
                    </Col>
                  </Row>
                </Form>

                {members.length === 0 ? (
                  <p className="text-muted mb-0 small">{t('dashboard.noTeamMemberships')}</p>
                ) : (
                  <Table size="sm" responsive className="mb-0">
                    <thead>
                      <tr>
                        <th>{t('common.name')}</th>
                        <th>{t('common.email')}</th>
                        <th>{t('common.role')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {members.map((member) => (
                        <tr key={member.user_id}>
                          <td className="fw-medium">{member.full_name || member.email}</td>
                          <td>{member.email}</td>
                          <td><Badge bg="secondary">{member.role}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                )}
              </div>
            </Tab>
          </Tabs>
        </Card.Body>
      </Card>
    </div>
  )
}

export default OrganizationSettings
