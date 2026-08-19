import React, { useEffect, useState } from 'react'
import { Alert, Card, Row, Col, Button, Table, Badge, Form, Collapse } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { FiPlus, FiUsers, FiCheckCircle, FiXCircle, FiEye, FiUserPlus, FiBarChart2, FiMail, FiActivity, FiCpu, FiSave } from 'react-icons/fi'
import StatCard from '../components/ui/StatCard'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'
import ErrorAlert from '../components/ui/ErrorAlert'
import ConfirmModal from '../components/ui/ConfirmModal'
import { useToast } from '../hooks/useToast'
import { useRealTimeRefresh } from '../hooks/useRealTimeRefresh'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement)

const STATUS_BG: Record<string, string> = {
  draft: 'secondary',
  active: 'success',
  completed: 'primary',
  cancelled: 'danger',
}

const EmployerDashboard: React.FC = () => {
  const [interviews, setInterviews] = useState<any[]>([])
  const [organization, setOrganization] = useState<any>(null)
  const [members, setMembers] = useState<any[]>([])
  const [evaluationHealth, setEvaluationHealth] = useState<any>(null)
  const [emailHealth, setEmailHealth] = useState<any>(null)
  const [providersInfo, setProvidersInfo] = useState<any>(null)
  const [providerSelection, setProviderSelection] = useState('')
  const [providerModel, setProviderModel] = useState('')
  const [providerBaseUrl, setProviderBaseUrl] = useState('')
  const [providerApiKey, setProviderApiKey] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [savingProvider, setSavingProvider] = useState(false)
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState('reviewer')
  const [teamError, setTeamError] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const navigate = useNavigate()
  const toast = useToast()
  const { t, i18n } = useTranslation()

  const statusLabelMap: Record<string, string> = {
    draft: t('dashboard.draft'),
    active: t('dashboard.active'),
    completed: t('dashboard.completed'),
    cancelled: t('dashboard.cancelled'),
  }

  const providerLabelMap: Record<string, string> = {
    '': t('dashboard.providerDefault'),
    local_vllm: t('dashboard.providerLocal'),
    cloud_llm: t('dashboard.providerCloud'),
    hybrid: t('dashboard.providerHybrid'),
  }

  const selectedProviderLabel = (selected: string | null | undefined) =>
    selected ? providerLabelMap[selected] || selected : providerLabelMap['']

  const handleSaveProvider = async (event: React.FormEvent) => {
    event.preventDefault()
    setSavingProvider(true)
    try {
      const response = await api.users.updateOrganizationSettings({
        evaluation_provider: providerSelection || '',
        evaluation_model: providerModel,
        evaluation_base_url: providerBaseUrl,
        evaluation_api_key: providerApiKey,
      })
      setOrganization(response.data)
      if (providersInfo) {
        setProvidersInfo({ ...providersInfo, selected: response.data.evaluation_provider })
      }
      setProviderApiKey('')
      toast.success(t('dashboard.providerSaved'))
    } catch {
      toast.error(t('dashboard.providerSaveFailed'))
    } finally {
      setSavingProvider(false)
    }
  }

  const getStatusBadge = (status: string) => (
    <Badge bg={STATUS_BG[status] || 'secondary'}>{statusLabelMap[status] || status.charAt(0).toUpperCase() + status.slice(1)}</Badge>
  )

  useEffect(() => {
    loadInterviews()
  }, [])

  const loadInterviews = async () => {
    try {
      const organizationResponse = await api.users.getMyOrganization()
      const org = organizationResponse.data
      setOrganization(org)
      setProviderModel(org.evaluation_model || '')
      setProviderBaseUrl(org.evaluation_base_url || '')
      const [interviewsResponse, membersResponse, evaluationHealthResponse, emailHealthResponse, providersResponse] = await Promise.all([
        api.interviews.list(),
        api.users.getOrganizationMembers(),
        api.reports.getEvaluationHealth(org?.id),
        api.reports.getEmailHealth(),
        api.users.getOrganizationProviders(),
      ])
      setInterviews(interviewsResponse.data)
      setMembers(membersResponse.data)
      setEvaluationHealth(evaluationHealthResponse.data)
      setEmailHealth(emailHealthResponse.data)
      setProvidersInfo(providersResponse.data)
      setProviderSelection(providersResponse.data.selected || '')
    } catch (error) {
      toast.error(t('dashboard.loadFailed'), t('dashboard.loadError'))
    } finally {
      setLoading(false)
    }
   }

   // Keep the dashboard in sync when interviews/responses/evaluations/decisions
   // change anywhere in the system, without a manual refresh.
   useRealTimeRefresh(loadInterviews, [])

   const handleAddMember = async (event: React.FormEvent) => {
    event.preventDefault()
    setTeamError('')
    setAddingMember(true)
    try {
      const response = await api.users.addMembership({ email: memberEmail, role: memberRole })
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

  const handleDelete = async () => {
    if (deletingId === null) return
    try {
      await api.interviews.delete(deletingId)
      setInterviews(prev => prev.filter(i => i.id !== deletingId))
      toast.success(t('dashboard.deleted'))
    } catch {
      toast.error(t('dashboard.deleteFailed'))
    } finally {
      setShowDeleteModal(false)
      setDeletingId(null)
    }
  }

  const activeCount = interviews.filter(i => i.status === 'active').length
  const completedCount = interviews.filter(i => i.status === 'completed').length
  const draftCount = interviews.filter(i => i.status === 'draft').length

  const statusChartData = {
    labels: [t('dashboard.active'), t('dashboard.completed'), t('dashboard.draft'), t('dashboard.cancelled')],
    datasets: [{
      data: [activeCount, completedCount, draftCount, interviews.length - activeCount - completedCount - draftCount],
      backgroundColor: ['#10b981', '#4f46e5', '#f59e0b', '#ef4444'],
      borderWidth: 0,
    }],
  }

  const monthFormatter = new Intl.DateTimeFormat(i18n.language === 'ar' ? 'ar' : 'en', { month: 'short' })

  const monthlyData = (() => {
    const months: { key: string; label: string; count: number }[] = []
    const now = new Date()
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      months.push({ key: `${d.getFullYear()}-${d.getMonth()}`, label: monthFormatter.format(d), count: 0 })
    }
    interviews.forEach((interview) => {
      if (!interview.created_at) return
      const created = new Date(interview.created_at)
      const month = months.find((m) => m.key === `${created.getFullYear()}-${created.getMonth()}`)
      if (month) month.count += 1
    })
    return {
      labels: months.map((m) => m.label),
      datasets: [{
        label: t('dashboard.interviews'),
        data: months.map((m) => m.count),
        backgroundColor: 'var(--color-primary)',
        borderRadius: 6,
      }],
    }
  })()

  if (loading) return <LoadingSpinner text={t('dashboard.loading')} />

  return (
    <div>
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        actions={
          <Button variant="primary" onClick={() => navigate('/employer/interviews/create')}>
            <FiPlus className="me-2" />
            {t('dashboard.createInterview')}
          </Button>
        }
      />

      <Row className="mb-4 g-3">
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiBarChart2 />} label={t('dashboard.totalInterviews')} value={interviews.length} />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiCheckCircle />} label={t('dashboard.active')} value={activeCount} variant="success" />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiUsers />} label={t('dashboard.completed')} value={completedCount} variant="info" />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiXCircle />} label={t('dashboard.teamMembers')} value={members.length} variant="warning" />
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col md={7}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">{t('dashboard.interviewTrends')}</h6>
            </Card.Header>
            <Card.Body>
              <Bar data={monthlyData} options={{ responsive: true, plugins: { legend: { display: false } } }} />
            </Card.Body>
          </Card>
        </Col>
        <Col md={5}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">{t('dashboard.statusDistribution')}</h6>
            </Card.Header>
            <Card.Body className="d-flex align-items-center justify-content-center">
              {interviews.length === 0 ? (
                <p className="text-muted mb-0">{t('dashboard.noInterviewsYet')}</p>
              ) : (
                <div style={{ maxWidth: 220 }}>
                  <Doughnut data={statusChartData} options={{ cutout: '70%', plugins: { legend: { position: 'bottom' } } }} />
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col md={6}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold d-flex align-items-center gap-2">
                <FiActivity /> {t('dashboard.evaluationAgent')}
              </h6>
            </Card.Header>
            <Card.Body>
              {evaluationHealth ? (
                <Row>
                  <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.status')}</p><Badge bg={evaluationHealth.healthy ? 'success' : 'warning'}>{evaluationHealth.status}</Badge></Col>
                  <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.provider')}</p><p className="mb-0 fw-medium">{evaluationHealth.provider}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.model')}</p><p className="mb-0 fw-medium">{evaluationHealth.model_name || t('common.n/a')}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.fallback')}</p><p className="mb-0 fw-medium">{evaluationHealth.fallback_provider || t('common.n/a')}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.promptVersion')}</p><p className="mb-0 fw-medium">{evaluationHealth.prompt_version || t('common.n/a')}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.configHash')}</p><p className="mb-0 fw-medium">{evaluationHealth.config_hash || t('common.n/a')}</p></Col>
                  {evaluationHealth.last_error && (
                    <Col xs={12} className="mt-3"><Alert variant="warning" className="mb-0 py-2 small">{evaluationHealth.last_error}</Alert></Col>
                  )}
                </Row>
              ) : (
                <p className="text-muted mb-0 small">{t('dashboard.unavailable')}</p>
              )}
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold d-flex align-items-center gap-2">
                <FiMail /> {t('dashboard.emailDelivery')}
              </h6>
            </Card.Header>
            <Card.Body>
              {emailHealth ? (
                <Row>
                  <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.status')}</p><Badge bg={emailHealth.configured ? 'success' : 'warning'}>{emailHealth.status}</Badge></Col>
                  <Col xs={6}><p className="mb-1 text-muted small">{t('dashboard.from')}</p><p className="mb-0 fw-medium">{emailHealth.mail_from}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.server')}</p><p className="mb-0 fw-medium">{emailHealth.mail_server}:{emailHealth.mail_port}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">{t('dashboard.missing')}</p><p className="mb-0 fw-medium">{emailHealth.missing_settings?.length ? emailHealth.missing_settings.join(', ') : t('common.none')}</p></Col>
                </Row>
              ) : (
                <p className="text-muted mb-0 small">{t('dashboard.unavailable')}</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col>
          <Card>
            <Card.Header>
              <h6 className="mb-0 fw-semibold d-flex align-items-center gap-2">
                <FiCpu /> {t('dashboard.providerSettings')}
              </h6>
            </Card.Header>
            <Card.Body>
              <p className="text-muted small mb-3">{t('dashboard.providerSettingsSubtitle')}</p>
              {providersInfo ? (
                providersInfo.role === 'owner' || providersInfo.role === 'admin' ? (
                  <Form onSubmit={handleSaveProvider}>
                    <Row className="g-3 align-items-end">
                      <Col md={6} xl={4}>
                        <Form.Label className="small text-muted">{t('dashboard.provider')}</Form.Label>
                        <Form.Select
                          value={providerSelection}
                          onChange={(e) => setProviderSelection(e.target.value)}
                          size="sm"
                          aria-label={t('dashboard.provider')}
                        >
                          <option value="">{t('dashboard.providerDefault')}</option>
                          {providersInfo.providers.map((p: any) => (
                            <option key={p.value} value={p.value} disabled={!p.available}>
                              {providerLabelMap[p.value] || p.value}
                              {!p.available ? ` (${t('dashboard.providerUnavailable')})` : ''}
                            </option>
                          ))}
                        </Form.Select>
                      </Col>
                      <Col md={3} xl={2}>
                        <Button type="submit" variant="primary" size="sm" className="w-100" disabled={savingProvider}>
                          <FiSave className="me-1" /> {t('common.save')}
                        </Button>
                      </Col>
                    </Row>
                    <Button
                      variant="link"
                      size="sm"
                      className="p-0 mt-2 text-decoration-none"
                      onClick={() => setShowAdvanced((s) => !s)}
                      aria-expanded={showAdvanced}
                    >
                      {t('dashboard.providerAdvanced')}
                    </Button>
                    <Collapse in={showAdvanced}>
                      <div>
                        <Row className="g-3 mt-0">
                          <Col md={4}>
                            <Form.Label className="small text-muted">{t('dashboard.providerModel')}</Form.Label>
                            <Form.Control size="sm" type="text" value={providerModel} onChange={(e) => setProviderModel(e.target.value)} />
                          </Col>
                          <Col md={4}>
                            <Form.Label className="small text-muted">{t('dashboard.providerBaseUrl')}</Form.Label>
                            <Form.Control size="sm" type="text" value={providerBaseUrl} onChange={(e) => setProviderBaseUrl(e.target.value)} />
                          </Col>
                          <Col md={4}>
                            <Form.Label className="small text-muted">{t('dashboard.providerApiKey')}</Form.Label>
                            <Form.Control size="sm" type="password" value={providerApiKey} onChange={(e) => setProviderApiKey(e.target.value)} autoComplete="off" />
                          </Col>
                        </Row>
                      </div>
                    </Collapse>
                  </Form>
                ) : (
                  <p className="mb-0">
                    <Badge bg="secondary" pill>{selectedProviderLabel(providersInfo.selected)}</Badge>{' '}
                    <span className="text-muted small">{t('dashboard.providerReadOnly')}</span>
                  </p>
                )
              ) : (
                <p className="text-muted mb-0 small">{t('dashboard.unavailable')}</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col lg={5}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">{t('dashboard.organization')}</h6>
            </Card.Header>
            <Card.Body>
              {organization ? (
                <>
                  <h4 className="fw-bold">{organization.name}</h4>
                  <p className="text-muted mb-0">{t('dashboard.teamMembersCount', { count: members.length })}</p>
                </>
              ) : (
                <p className="text-muted mb-0">{t('dashboard.noOrganization')}</p>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={7}>
          <Card>
            <Card.Header>
              <h6 className="mb-0 fw-semibold">{t('dashboard.teamAccess')}</h6>
            </Card.Header>
            <Card.Body>
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
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card>
        <Card.Header>
          <h6 className="mb-0 fw-semibold">{t('dashboard.yourInterviews')}</h6>
        </Card.Header>
        <Card.Body>
          {interviews.length === 0 ? (
            <EmptyState
              title={t('dashboard.noInterviewsYet')}
              description={t('dashboard.createFirst')}
              actionLabel={t('dashboard.createInterview')}
              onAction={() => navigate('/employer/interviews/create')}
            />
          ) : (
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>{t('common.title')}</th>
                  <th>{t('common.status')}</th>
                  <th>{t('dashboard.duration')}</th>
                  <th>{t('dashboard.passScore')}</th>
                  <th>{t('dashboard.created')}</th>
                  <th>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {interviews.map((interview) => (
                  <tr key={interview.id}>
                    <td className="fw-medium">{interview.title}</td>
                    <td>{getStatusBadge(interview.status)}</td>
                    <td>{t('dashboard.minutesShort', { count: interview.duration_minutes })}</td>
                    <td>{interview.pass_score}%</td>
                    <td className="text-muted small">{new Date(interview.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="d-flex gap-2">
                        <Button variant="outline-primary" size="sm" onClick={() => navigate(`/employer/interviews/${interview.id}`)}>
                          <FiEye /> {t('common.view')}
                        </Button>
                        {interview.status === 'draft' && (
                          <Button variant="outline-danger" size="sm" onClick={() => { setDeletingId(interview.id); setShowDeleteModal(true) }}>
                            {t('dashboard.delete')}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>

      <ConfirmModal
        show={showDeleteModal}
        title={t('dashboard.deleteTitle')}
        message={t('dashboard.deleteConfirm')}
        confirmLabel={t('dashboard.delete')}
        onConfirm={handleDelete}
        onCancel={() => { setShowDeleteModal(false); setDeletingId(null) }}
      />
    </div>
  )
}

export default EmployerDashboard
