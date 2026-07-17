import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Table, Badge, Modal, Form, Alert, Tabs, Tab } from 'react-bootstrap'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import { FiMail, FiDownload, FiEye, FiActivate } from 'react-icons/fi'

const InterviewDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [interview, setInterview] = useState<any>(null)
  const [responses, setResponses] = useState<any[]>([])
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [invitations, setInvitations] = useState<any[]>([])
  const [inviteData, setInviteData] = useState({ candidate_email: '', candidate_name: '' })
  const [bulkInvites, setBulkInvites] = useState('')
  const [inviteTab, setInviteTab] = useState('single')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadData()
  }, [id])
  
  const loadData = async () => {
    try {
      const [interviewRes, responsesRes, invitationsRes] = await Promise.all([
        api.interviews.get(parseInt(id!)),
        api.responses.list(parseInt(id!)),
        api.invitations.list(parseInt(id!))
      ])
      setInterview(interviewRes.data)
      setResponses(responsesRes.data)
      setInvitations(invitationsRes.data)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleActivate = async () => {
    if (!confirm('Activate this interview? Candidates will be able to start taking it.')) {
      return
    }
    
    try {
      await api.interviews.activate(parseInt(id!))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to activate')
    }
  }
  
  const handleComplete = async () => {
    if (!confirm('Complete this interview? No more candidates will be able to join.')) {
      return
    }
    
    try {
      await api.interviews.complete(parseInt(id!))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete')
    }
  }
  
  const handleInvite = async () => {
    setError('')
    try {
      await api.invitations.create({
        interview_id: parseInt(id!),
        ...inviteData
      })
      setShowInviteModal(false)
      setInviteData({ candidate_email: '', candidate_name: '' })
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send invitation')
    }
  }
  
  const handleBulkInvite = async () => {
    setError('')
    try {
      const lines = bulkInvites.trim().split('\n')
      const invitations = lines.map(line => {
        const [email, name] = line.split(',').map(s => s.trim())
        return { interview_id: parseInt(id!), candidate_email: email, candidate_name: name || email }
      })
      
      await api.invitations.createBulk(invitations)
      setBulkInvites('')
      setInviteTab('list')
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send invitations')
    }
  }
  
  const handleDownloadReport = async () => {
    try {
      const response = await api.reports.downloadInterviewPdf(parseInt(id!))
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `interview_${id}_report.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to download report:', error)
    }
  }
  
  if (loading) {
    return <p>Loading...</p>
  }
  
  if (!interview) {
    return <p>Interview not found</p>
  }
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'draft': return <Badge bg="secondary">Draft</Badge>
      case 'active': return <Badge bg="success">Active</Badge>
      case 'completed': return <Badge bg="primary">Completed</Badge>
      default: return <Badge bg="secondary">{status}</Badge>
    }
  }
  
  const sortedResponses = [...responses].sort((a, b) => (b.total_score || 0) - (a.total_score || 0))
  
  return (
    <div>
      {error && <Alert variant="danger">{error}</Alert>}
      
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h1>{interview.title}</h1>
          <p className="text-muted">{getStatusBadge(interview.status)}</p>
        </div>
        <div className="d-flex gap-2">
          {interview.status === 'draft' && (
            <Button variant="success" onClick={handleActivate}>
              <FiActivate className="me-2" />
              Activate Interview
            </Button>
          )}
          {interview.status === 'active' && (
            <Button variant="warning" onClick={handleComplete}>
              Complete Interview
            </Button>
          )}
          <Button variant="outline-primary" onClick={() => setShowInviteModal(true)}>
            <FiMail className="me-2" />
            Invite Candidates
          </Button>
          {responses.length > 0 && (
            <Button variant="outline-dark" onClick={handleDownloadReport}>
              <FiDownload className="me-2" />
              Download Report
            </Button>
          )}
        </div>
      </div>
      
      <Row>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Interview Details</h5>
            </Card.Header>
            <Card.Body>
              <p><strong>Description:</strong> {interview.description || 'N/A'}</p>
              <p><strong>Duration:</strong> {interview.duration_minutes} minutes</p>
              <p><strong>Max Attempts:</strong> {interview.max_attempts}</p>
              <p><strong>Pass Score:</strong> {interview.pass_score}%</p>
              <p><strong>Created:</strong> {new Date(interview.created_at).toLocaleDateString()}</p>
            </Card.Body>
          </Card>
          
          <Card>
            <Card.Header>
              <h5 className="mb-0">Questions ({interview.questions?.length || 0})</h5>
            </Card.Header>
            <Card.Body>
              {interview.questions?.map((q: any, idx: number) => (
                <div key={q.id} className="mb-3">
                  <strong>Q{idx + 1}:</strong> {q.question_text}
                  <br />
                  <small className="text-muted">Weight: {q.weight}x</small>
                </div>
              ))}
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header>
              <h5 className="mb-0">Candidate Responses ({responses.length})</h5>
            </Card.Header>
            <Card.Body>
              {responses.length === 0 ? (
                <p className="text-center text-muted">No responses yet. Invite candidates to get started!</p>
              ) : (
                <Table striped bordered hover responsive>
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Score</th>
                      <th>Status</th>
                      <th>Confidence</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedResponses.map((response, idx) => (
                      <tr key={response.id}>
                        <td>
                          <Badge bg={idx === 0 ? 'warning' : idx === 1 ? 'secondary' : idx === 2 ? 'danger' : 'light'}>
                            #{idx + 1}
                          </Badge>
                        </td>
                        <td>{response.candidate_name}</td>
                        <td>{response.candidate_email}</td>
                        <td>
                          <Badge bg={response.total_score >= interview.pass_score ? 'success' : 'danger'}>
                            {response.total_score?.toFixed(1) || 0}%
                          </Badge>
                        </td>
                        <td>{response.status}</td>
                        <td>{response.confidence_score?.toFixed(1) || 'N/A'}%</td>
                        <td>
                          <Link to={`/employer/candidate/${response.id}`}>
                            <Button variant="outline-primary" size="sm">
                              <FiEye /> View Report
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
          
          <Card>
            <Card.Header>
              <h5 className="mb-0">Invitations ({invitations.length})</h5>
            </Card.Header>
            <Card.Body>
              {invitations.length === 0 ? (
                <p className="text-muted">No invitations sent yet</p>
              ) : (
                <Table size="sm">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Status</th>
                      <th>Sent</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invitations.map(inv => (
                      <tr key={inv.id}>
                        <td>{inv.candidate_name}</td>
                        <td>{inv.candidate_email}</td>
                        <td>
                          <Badge bg={
                            inv.status === 'completed' ? 'success' :
                            inv.status === 'sent' ? 'primary' :
                            inv.status === 'expired' ? 'danger' :
                            'secondary'
                          }>
                            {inv.status}
                          </Badge>
                        </td>
                        <td>{inv.sent_at ? new Date(inv.sent_at).toLocaleDateString() : 'Not sent'}</td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {/* Invite Modal */}
      <Modal show={showInviteModal} onHide={() => setShowInviteModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Invite Candidates</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Tabs activeKey={inviteTab} onSelect={(k) => setInviteTab(k || 'single')}>
            <Tab eventKey="single" title="Single Invite">
              <Form className="mt-3">
                <Form.Group className="mb-3">
                  <Form.Label>Candidate Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={inviteData.candidate_name}
                    onChange={(e) => setInviteData({...inviteData, candidate_name: e.target.value})}
                  />
                </Form.Group>
                <Form.Group className="mb-3">
                  <Form.Label>Candidate Email</Form.Label>
                  <Form.Control
                    type="email"
                    value={inviteData.candidate_email}
                    onChange={(e) => setInviteData({...inviteData, candidate_email: e.target.value})}
                  />
                </Form.Group>
                <Button variant="primary" onClick={handleInvite}>
                  Send Invitation
                </Button>
              </Form>
            </Tab>
            <Tab eventKey="bulk" title="Bulk Invite">
              <Form className="mt-3">
                <Form.Group className="mb-3">
                  <Form.Label>Enter candidates (one per line: email, name)</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={5}
                    value={bulkInvites}
                    onChange={(e) => setBulkInvites(e.target.value)}
                    placeholder={"john@example.com, John Doe\njane@example.com, Jane Smith"}
                  />
                </Form.Group>
                <Button variant="primary" onClick={handleBulkInvite}>
                  Send All Invitations
                </Button>
              </Form>
            </Tab>
            <Tab eventKey="list" title="Sent Invitations">
              <Table size="sm" className="mt-3">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map(inv => (
                    <tr key={inv.id}>
                      <td>{inv.candidate_name}</td>
                      <td>{inv.candidate_email}</td>
                      <td><Badge bg="secondary">{inv.status}</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Tab>
          </Tabs>
        </Modal.Body>
      </Modal>
    </div>
  )
}

export default InterviewDetail
