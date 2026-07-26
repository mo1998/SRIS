import React, { useEffect, useState } from 'react'
import { Alert, Card, Row, Col, Button, Table, Badge, Form } from 'react-bootstrap'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { FiPlus, FiUsers, FiCheckCircle, FiXCircle, FiEye, FiUserPlus, FiBarChart2, FiMail, FiActivity } from 'react-icons/fi'
import StatCard from '../components/ui/StatCard'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'
import ErrorAlert from '../components/ui/ErrorAlert'
import ConfirmModal from '../components/ui/ConfirmModal'
import { useToast } from '../hooks/useToast'
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

const getStatusBadge = (status: string) => (
  <Badge bg={STATUS_BG[status] || 'secondary'}>{status.charAt(0).toUpperCase() + status.slice(1)}</Badge>
)

const EmployerDashboard: React.FC = () => {
  const [interviews, setInterviews] = useState<any[]>([])
  const [organization, setOrganization] = useState<any>(null)
  const [memberships, setMemberships] = useState<any[]>([])
  const [evaluationHealth, setEvaluationHealth] = useState<any>(null)
  const [emailHealth, setEmailHealth] = useState<any>(null)
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState('reviewer')
  const [teamError, setTeamError] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const navigate = useNavigate()
  const toast = useToast()

  useEffect(() => {
    loadInterviews()
  }, [])

  const loadInterviews = async () => {
    try {
      const [interviewsResponse, organizationResponse, membershipsResponse, evaluationHealthResponse, emailHealthResponse] = await Promise.all([
        api.interviews.list(),
        api.users.getMyOrganization(),
        api.users.getMyMemberships(),
        api.reports.getEvaluationHealth(),
        api.reports.getEmailHealth()
      ])
      setInterviews(interviewsResponse.data)
      setOrganization(organizationResponse.data)
      setMemberships(membershipsResponse.data)
      setEvaluationHealth(evaluationHealthResponse.data)
      setEmailHealth(emailHealthResponse.data)
    } catch (error) {
      toast.error('Failed to load dashboard', 'Could not fetch dashboard data')
    } finally {
      setLoading(false)
    }
  }

  const handleAddMember = async (event: React.FormEvent) => {
    event.preventDefault()
    setTeamError('')
    setAddingMember(true)
    try {
      const response = await api.users.addMembership({ email: memberEmail, role: memberRole })
      setMemberships((current) => [...current, response.data])
      setMemberEmail('')
      setMemberRole('reviewer')
      toast.success('Team member added')
    } catch (err: any) {
      setTeamError(err.response?.data?.detail || 'Failed to add team member')
    } finally {
      setAddingMember(false)
    }
  }

  const handleDelete = async () => {
    if (deletingId === null) return
    try {
      await api.interviews.delete(deletingId)
      setInterviews(prev => prev.filter(i => i.id !== deletingId))
      toast.success('Interview deleted')
    } catch {
      toast.error('Failed to delete interview')
    } finally {
      setShowDeleteModal(false)
      setDeletingId(null)
    }
  }

  const activeCount = interviews.filter(i => i.status === 'active').length
  const completedCount = interviews.filter(i => i.status === 'completed').length
  const draftCount = interviews.filter(i => i.status === 'draft').length

  const statusChartData = {
    labels: ['Active', 'Completed', 'Draft', 'Cancelled'],
    datasets: [{
      data: [activeCount, completedCount, draftCount, interviews.length - activeCount - completedCount - draftCount],
      backgroundColor: ['#10b981', '#4f46e5', '#f59e0b', '#ef4444'],
      borderWidth: 0,
    }],
  }

  const monthlyData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    datasets: [{
      label: 'Interviews',
      data: [2, 4, 3, 6, 5, 8],
      backgroundColor: 'var(--color-primary)',
      borderRadius: 6,
    }],
  }

  if (loading) return <LoadingSpinner text="Loading dashboard..." />

  return (
    <div>
      <PageHeader
        title="Employer Dashboard"
        subtitle="Overview of your organization's interview activity"
        actions={
          <Button variant="primary" onClick={() => navigate('/employer/interviews/create')}>
            <FiPlus className="me-2" />
            Create Interview
          </Button>
        }
      />

      <Row className="mb-4 g-3">
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiBarChart2 />} label="Total Interviews" value={interviews.length} />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiCheckCircle />} label="Active" value={activeCount} variant="success" />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiUsers />} label="Completed" value={completedCount} variant="info" />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiXCircle />} label="Team Members" value={memberships.length} variant="warning" />
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col md={7}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">Interview Trends</h6>
            </Card.Header>
            <Card.Body>
              <Bar data={monthlyData} options={{ responsive: true, plugins: { legend: { display: false } } }} />
            </Card.Body>
          </Card>
        </Col>
        <Col md={5}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">Status Distribution</h6>
            </Card.Header>
            <Card.Body className="d-flex align-items-center justify-content-center">
              {interviews.length === 0 ? (
                <p className="text-muted mb-0">No interviews yet</p>
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
                <FiActivity /> Evaluation Agent
              </h6>
            </Card.Header>
            <Card.Body>
              {evaluationHealth ? (
                <Row>
                  <Col xs={6}><p className="mb-1 text-muted small">Status</p><Badge bg={evaluationHealth.healthy ? 'success' : 'warning'}>{evaluationHealth.status}</Badge></Col>
                  <Col xs={6}><p className="mb-1 text-muted small">Provider</p><p className="mb-0 fw-medium">{evaluationHealth.provider}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">Model</p><p className="mb-0 fw-medium">{evaluationHealth.model_name || 'N/A'}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">Fallback</p><p className="mb-0 fw-medium">{evaluationHealth.fallback_provider || 'N/A'}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">Prompt Version</p><p className="mb-0 fw-medium">{evaluationHealth.prompt_version || 'N/A'}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">Config Hash</p><p className="mb-0 fw-medium">{evaluationHealth.config_hash || 'N/A'}</p></Col>
                  {evaluationHealth.last_error && (
                    <Col xs={12} className="mt-3"><Alert variant="warning" className="mb-0 py-2 small">{evaluationHealth.last_error}</Alert></Col>
                  )}
                </Row>
              ) : (
                <p className="text-muted mb-0 small">Unavailable.</p>
              )}
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold d-flex align-items-center gap-2">
                <FiMail /> Email Delivery
              </h6>
            </Card.Header>
            <Card.Body>
              {emailHealth ? (
                <Row>
                  <Col xs={6}><p className="mb-1 text-muted small">Status</p><Badge bg={emailHealth.configured ? 'success' : 'warning'}>{emailHealth.status}</Badge></Col>
                  <Col xs={6}><p className="mb-1 text-muted small">From</p><p className="mb-0 fw-medium">{emailHealth.mail_from}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">Server</p><p className="mb-0 fw-medium">{emailHealth.mail_server}:{emailHealth.mail_port}</p></Col>
                  <Col xs={6} className="mt-3"><p className="mb-1 text-muted small">Missing</p><p className="mb-0 fw-medium">{emailHealth.missing_settings?.length ? emailHealth.missing_settings.join(', ') : 'None'}</p></Col>
                </Row>
              ) : (
                <p className="text-muted mb-0 small">Unavailable.</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col lg={5}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">Organization</h6>
            </Card.Header>
            <Card.Body>
              {organization ? (
                <>
                  <h4 className="fw-bold">{organization.name}</h4>
                  <p className="text-muted mb-0">Team members: {memberships.length}</p>
                </>
              ) : (
                <p className="text-muted mb-0">No organization found.</p>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={7}>
          <Card>
            <Card.Header>
              <h6 className="mb-0 fw-semibold">Team Access</h6>
            </Card.Header>
            <Card.Body>
              <ErrorAlert message={teamError} onClose={() => setTeamError('')} />

              <Form onSubmit={handleAddMember} className="mb-3">
                <Row className="g-2 align-items-end">
                  <Col md={6}>
                    <Form.Label className="small text-muted">Email</Form.Label>
                    <Form.Control type="email" value={memberEmail} onChange={(e) => setMemberEmail(e.target.value)}
                      placeholder="teammate@example.com" required size="sm" />
                  </Col>
                  <Col md={4}>
                    <Form.Label className="small text-muted">Role</Form.Label>
                    <Form.Select value={memberRole} onChange={(e) => setMemberRole(e.target.value)} size="sm">
                      <option value="reviewer">Reviewer</option>
                      <option value="recruiter">Recruiter</option>
                      <option value="admin">Admin</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Button type="submit" variant="outline-primary" className="w-100" disabled={addingMember} size="sm">
                      <FiUserPlus className="me-1" /> Add
                    </Button>
                  </Col>
                </Row>
              </Form>

              {memberships.length === 0 ? (
                <p className="text-muted mb-0 small">No team memberships found.</p>
              ) : (
                <Table size="sm" responsive className="mb-0">
                  <thead>
                    <tr>
                      <th>User ID</th>
                      <th>Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    {memberships.map((membership) => (
                      <tr key={membership.id}>
                        <td>{membership.user_id}</td>
                        <td><Badge bg="secondary">{membership.role}</Badge></td>
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
          <h6 className="mb-0 fw-semibold">Your Interviews</h6>
        </Card.Header>
        <Card.Body>
          {interviews.length === 0 ? (
            <EmptyState
              title="No interviews yet"
              description="Create your first interview to get started."
              actionLabel="Create Interview"
              onAction={() => navigate('/employer/interviews/create')}
            />
          ) : (
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Pass Score</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {interviews.map((interview) => (
                  <tr key={interview.id}>
                    <td className="fw-medium">{interview.title}</td>
                    <td>{getStatusBadge(interview.status)}</td>
                    <td>{interview.duration_minutes} min</td>
                    <td>{interview.pass_score}%</td>
                    <td className="text-muted small">{new Date(interview.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="d-flex gap-2">
                        <Button variant="outline-primary" size="sm" onClick={() => navigate(`/employer/interviews/${interview.id}`)}>
                          <FiEye /> View
                        </Button>
                        {interview.status === 'draft' && (
                          <Button variant="outline-danger" size="sm" onClick={() => { setDeletingId(interview.id); setShowDeleteModal(true) }}>
                            Delete
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
        title="Delete Interview"
        message="Are you sure you want to delete this interview? This action cannot be undone."
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => { setShowDeleteModal(false); setDeletingId(null) }}
      />
    </div>
  )
}

export default EmployerDashboard
