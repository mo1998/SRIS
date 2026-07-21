import React, { useEffect, useState } from 'react'
import { Alert, Card, Row, Col, Button, Table, Badge, Form } from 'react-bootstrap'
import { api } from '../services/api'
import { Link } from 'react-router-dom'
import { FiPlus, FiUsers, FiCheckCircle, FiXCircle, FiEye, FiUserPlus } from 'react-icons/fi'

const EmployerDashboard: React.FC = () => {
  const [interviews, setInterviews] = useState<any[]>([])
  const [organization, setOrganization] = useState<any>(null)
  const [memberships, setMemberships] = useState<any[]>([])
  const [evaluationHealth, setEvaluationHealth] = useState<any>(null)
  const [emailHealth, setEmailHealth] = useState<any>(null)
  const [memberEmail, setMemberEmail] = useState('')
  const [memberRole, setMemberRole] = useState('reviewer')
  const [teamError, setTeamError] = useState('')
  const [teamMessage, setTeamMessage] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [loading, setLoading] = useState(true)
  
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
      console.error('Failed to load dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddMember = async (event: React.FormEvent) => {
    event.preventDefault()
    setTeamError('')
    setTeamMessage('')
    setAddingMember(true)

    try {
      const response = await api.users.addMembership({ email: memberEmail, role: memberRole })
      setMemberships((current) => [...current, response.data])
      setMemberEmail('')
      setMemberRole('reviewer')
      setTeamMessage('Team member added')
    } catch (err: any) {
      setTeamError(err.response?.data?.detail || 'Failed to add team member')
    } finally {
      setAddingMember(false)
    }
  }
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'draft':
        return <Badge bg="secondary">Draft</Badge>
      case 'active':
        return <Badge bg="success">Active</Badge>
      case 'completed':
        return <Badge bg="primary">Completed</Badge>
      case 'cancelled':
        return <Badge bg="danger">Cancelled</Badge>
      default:
        return <Badge bg="secondary">{status}</Badge>
    }
  }
  
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Employer Dashboard</h1>
        <Link to="/employer/interviews/create">
          <Button variant="primary">
            <FiPlus className="me-2" />
            Create Interview
          </Button>
        </Link>
      </div>
      
      <Row className="mb-4">
        <Col md={4}>
          <Card>
            <Card.Body>
              <Card.Title>
                <FiUsers className="me-2" />
                Total Interviews
              </Card.Title>
              <Card.Text className="display-4">{interviews.length}</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card>
            <Card.Body>
              <Card.Title>
                <FiCheckCircle className="me-2" />
                Active Interviews
              </Card.Title>
              <Card.Text className="display-4">
                {interviews.filter(i => i.status === 'active').length}
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card>
            <Card.Body>
              <Card.Title>
                <FiXCircle className="me-2" />
                Completed Interviews
              </Card.Title>
              <Card.Text className="display-4">
                {interviews.filter(i => i.status === 'completed').length}
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">Evaluation Agent Health</h5>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <p>Loading...</p>
          ) : evaluationHealth ? (
            <Row>
              <Col md={3}>
                <p className="mb-1"><strong>Status</strong></p>
                <Badge bg={evaluationHealth.healthy ? 'success' : 'warning'}>{evaluationHealth.status}</Badge>
              </Col>
              <Col md={3}>
                <p className="mb-1"><strong>Provider</strong></p>
                <p className="mb-0">{evaluationHealth.provider}</p>
              </Col>
              <Col md={3}>
                <p className="mb-1"><strong>Model</strong></p>
                <p className="mb-0">{evaluationHealth.model_name || 'N/A'}</p>
              </Col>
              <Col md={3}>
                <p className="mb-1"><strong>Fallback</strong></p>
                <p className="mb-0">{evaluationHealth.fallback_provider || 'N/A'}</p>
              </Col>
              <Col md={6} className="mt-3">
                <p className="mb-1"><strong>Prompt Version</strong></p>
                <p className="mb-0">{evaluationHealth.prompt_version || 'N/A'}</p>
              </Col>
              <Col md={6} className="mt-3">
                <p className="mb-1"><strong>Config Hash</strong></p>
                <p className="mb-0">{evaluationHealth.config_hash || 'N/A'}</p>
              </Col>
              {evaluationHealth.last_error && (
                <Col xs={12} className="mt-3">
                  <Alert variant="warning" className="mb-0">{evaluationHealth.last_error}</Alert>
                </Col>
              )}
            </Row>
          ) : (
            <p className="text-muted mb-0">Evaluation health is unavailable.</p>
          )}
        </Card.Body>
      </Card>

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">Email Delivery Health</h5>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <p>Loading...</p>
          ) : emailHealth ? (
            <Row>
              <Col md={3}>
                <p className="mb-1"><strong>Status</strong></p>
                <Badge bg={emailHealth.configured ? 'success' : 'warning'}>{emailHealth.status}</Badge>
              </Col>
              <Col md={3}>
                <p className="mb-1"><strong>From</strong></p>
                <p className="mb-0">{emailHealth.mail_from}</p>
              </Col>
              <Col md={3}>
                <p className="mb-1"><strong>Server</strong></p>
                <p className="mb-0">{emailHealth.mail_server}:{emailHealth.mail_port}</p>
              </Col>
              <Col md={3}>
                <p className="mb-1"><strong>Missing</strong></p>
                <p className="mb-0">{emailHealth.missing_settings?.length ? emailHealth.missing_settings.join(', ') : 'None'}</p>
              </Col>
            </Row>
          ) : (
            <p className="text-muted mb-0">Email health is unavailable.</p>
          )}
        </Card.Body>
      </Card>

      <Row className="mb-4">
        <Col lg={5} className="mb-4 mb-lg-0">
          <Card className="h-100">
            <Card.Header>
              <h5 className="mb-0">Organization</h5>
            </Card.Header>
            <Card.Body>
              {loading ? (
                <p>Loading...</p>
              ) : organization ? (
                <>
                  <h4>{organization.name}</h4>
                  <p className="text-muted mb-0">Team members: {memberships.length}</p>
                </>
              ) : (
                <p className="text-muted mb-0">No organization found for this account.</p>
              )}
            </Card.Body>
          </Card>
        </Col>

        <Col lg={7}>
          <Card className="h-100">
            <Card.Header>
              <h5 className="mb-0">Team Access</h5>
            </Card.Header>
            <Card.Body>
              {teamError && <Alert variant="danger">{teamError}</Alert>}
              {teamMessage && <Alert variant="success">{teamMessage}</Alert>}

              <Form onSubmit={handleAddMember} className="mb-3">
                <Row className="g-2 align-items-end">
                  <Col md={6}>
                    <Form.Label>Email</Form.Label>
                    <Form.Control
                      type="email"
                      value={memberEmail}
                      onChange={(event) => setMemberEmail(event.target.value)}
                      placeholder="teammate@example.com"
                      required
                    />
                  </Col>
                  <Col md={4}>
                    <Form.Label>Role</Form.Label>
                    <Form.Select value={memberRole} onChange={(event) => setMemberRole(event.target.value)}>
                      <option value="reviewer">Reviewer</option>
                      <option value="recruiter">Recruiter</option>
                      <option value="admin">Admin</option>
                    </Form.Select>
                  </Col>
                  <Col md={2}>
                    <Button type="submit" variant="outline-primary" className="w-100" disabled={addingMember}>
                      <FiUserPlus className="me-1" />
                      Add
                    </Button>
                  </Col>
                </Row>
              </Form>

              {loading ? (
                <p>Loading...</p>
              ) : memberships.length === 0 ? (
                <p className="text-muted mb-0">No team memberships found.</p>
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
          <h5 className="mb-0">Your Interviews</h5>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <p>Loading...</p>
          ) : interviews.length === 0 ? (
            <p className="text-center">No interviews created yet. Create your first interview!</p>
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
                    <td>{interview.title}</td>
                    <td>{getStatusBadge(interview.status)}</td>
                    <td>{interview.duration_minutes} min</td>
                    <td>{interview.pass_score}%</td>
                    <td>{new Date(interview.created_at).toLocaleDateString()}</td>
                    <td>
                      <Link to={`/employer/interviews/${interview.id}`}>
                        <Button variant="outline-primary" size="sm">
                          <FiEye className="me-1" />
                          View
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </div>
  )
}

export default EmployerDashboard
