import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Table, Badge, Modal, Form, Alert, Tabs, Tab } from 'react-bootstrap'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import { FiMail, FiDownload, FiEye, FiActivity, FiEdit, FiPlus, FiTrash2 } from 'react-icons/fi'

const InterviewDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const [interview, setInterview] = useState<any>(null)
  const [responses, setResponses] = useState<any[]>([])
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [invitations, setInvitations] = useState<any[]>([])
  const [inviteData, setInviteData] = useState({ candidate_email: '', candidate_name: '' })
  const [bulkInvites, setBulkInvites] = useState('')
  const [bulkInviteErrors, setBulkInviteErrors] = useState<string[]>([])
  const [invitationMessage, setInvitationMessage] = useState('')
  const [emailPreview, setEmailPreview] = useState<any>(null)
  const [previewError, setPreviewError] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [inviteTab, setInviteTab] = useState('single')
  const [isEditingDetails, setIsEditingDetails] = useState(false)
  const [isEditingQuestions, setIsEditingQuestions] = useState(false)
  const [editData, setEditData] = useState({
    title: '',
    description: '',
    duration_minutes: 30,
    max_attempts: 1,
    pass_score: 70,
  })
  const [questionDrafts, setQuestionDrafts] = useState<any[]>([])
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
      setEditData({
        title: interviewRes.data.title || '',
        description: interviewRes.data.description || '',
        duration_minutes: interviewRes.data.duration_minutes || 30,
        max_attempts: interviewRes.data.max_attempts || 1,
        pass_score: interviewRes.data.pass_score || 70,
      })
      setQuestionDrafts(normalizeQuestions(interviewRes.data.questions || []))
      setResponses(responsesRes.data)
      setInvitations(invitationsRes.data)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const normalizeQuestions = (questions: any[]) => questions.map((question, index) => ({
    question_text: question.question_text || '',
    expected_answer: question.expected_answer || '',
    question_type: question.question_type || 'text',
    weight: question.weight || 1,
    order_index: index,
    rubric_criteria: (question.rubric_criteria || []).map((criterion: any, criterionIndex: number) => ({
      name: criterion.name || '',
      description: criterion.description || '',
      weight: criterion.weight || 1,
      order_index: criterionIndex,
    })),
  }))
  
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

  const handleUpdateDetails = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')

    try {
      const response = await api.interviews.update(parseInt(id!), editData)
      setInterview(response.data)
      setEditData({
        title: response.data.title || '',
        description: response.data.description || '',
        duration_minutes: response.data.duration_minutes || 30,
        max_attempts: response.data.max_attempts || 1,
        pass_score: response.data.pass_score || 70,
      })
      setIsEditingDetails(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update interview')
    }
  }

  const updateQuestionDraft = (questionIndex: number, field: string, value: any) => {
    setQuestionDrafts((current) => current.map((question, index) => (
      index === questionIndex ? { ...question, [field]: value } : question
    )))
  }

  const addQuestionDraft = () => {
    setQuestionDrafts((current) => [
      ...current,
      { question_text: '', expected_answer: '', question_type: 'text', weight: 1, order_index: current.length, rubric_criteria: [] },
    ])
  }

  const removeQuestionDraft = (questionIndex: number) => {
    setQuestionDrafts((current) => current.filter((_, index) => index !== questionIndex))
  }

  const addCriterionDraft = (questionIndex: number) => {
    setQuestionDrafts((current) => current.map((question, index) => {
      if (index !== questionIndex) return question
      const criteria = question.rubric_criteria || []
      return {
        ...question,
        rubric_criteria: [...criteria, { name: '', description: '', weight: 1, order_index: criteria.length }],
      }
    }))
  }

  const updateCriterionDraft = (questionIndex: number, criterionIndex: number, field: string, value: any) => {
    setQuestionDrafts((current) => current.map((question, index) => {
      if (index !== questionIndex) return question
      return {
        ...question,
        rubric_criteria: (question.rubric_criteria || []).map((criterion: any, currentCriterionIndex: number) => (
          currentCriterionIndex === criterionIndex ? { ...criterion, [field]: value } : criterion
        )),
      }
    }))
  }

  const removeCriterionDraft = (questionIndex: number, criterionIndex: number) => {
    setQuestionDrafts((current) => current.map((question, index) => {
      if (index !== questionIndex) return question
      return {
        ...question,
        rubric_criteria: (question.rubric_criteria || []).filter((_: any, currentCriterionIndex: number) => currentCriterionIndex !== criterionIndex),
      }
    }))
  }

  const handleUpdateQuestions = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')

    try {
      const response = await api.interviews.update(parseInt(id!), {
        title: interview.title,
        description: interview.description,
        duration_minutes: interview.duration_minutes,
        max_attempts: interview.max_attempts,
        pass_score: interview.pass_score,
        questions: questionDrafts.map((question, questionIndex) => ({
          ...question,
          order_index: questionIndex,
          rubric_criteria: (question.rubric_criteria || [])
            .filter((criterion: any) => criterion.name.trim())
            .map((criterion: any, criterionIndex: number) => ({ ...criterion, order_index: criterionIndex })),
        })),
      })
      setInterview(response.data)
      setQuestionDrafts(normalizeQuestions(response.data.questions || []))
      setIsEditingQuestions(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update questions')
    }
  }
  
  const handleInvite = async () => {
    setError('')
    try {
      await api.invitations.create({
        interview_id: parseInt(id!),
        ...inviteData,
        custom_message: invitationMessage.trim() || undefined,
      })
      setShowInviteModal(false)
      setInviteData({ candidate_email: '', candidate_name: '' })
      setInvitationMessage('')
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send invitation')
    }
  }
  
  const handleBulkInvite = async () => {
    setError('')
    setBulkInviteErrors([])

    const lines = bulkInvites
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
    const parsedInvitations: Array<{ interview_id: number; candidate_email: string; candidate_name: string; custom_message?: string }> = []
    const validationErrors: string[] = []
    const seenEmails = new Set<string>()

    lines.forEach((line, index) => {
      const [email = '', name = '', ...extraColumns] = line.split(',').map((value) => value.trim())
      const rowNumber = index + 1
      let rowHasErrors = false

      if (extraColumns.length > 0) {
        validationErrors.push(`Row ${rowNumber}: use only email, name`)
        rowHasErrors = true
      }
      if (!email) {
        validationErrors.push(`Row ${rowNumber}: email is required`)
        rowHasErrors = true
      } else if (!/^\S+@\S+\.\S+$/.test(email)) {
        validationErrors.push(`Row ${rowNumber}: email is invalid`)
        rowHasErrors = true
      } else if (seenEmails.has(email.toLowerCase())) {
        validationErrors.push(`Row ${rowNumber}: duplicate email`)
        rowHasErrors = true
      } else {
        seenEmails.add(email.toLowerCase())
      }
      if (!name) {
        validationErrors.push(`Row ${rowNumber}: name is required`)
        rowHasErrors = true
      }

      if (!rowHasErrors) {
        parsedInvitations.push({
          interview_id: parseInt(id!),
          candidate_email: email,
          candidate_name: name,
          custom_message: invitationMessage.trim() || undefined,
        })
      }
    })

    if (lines.length === 0) {
      validationErrors.push('Add at least one candidate')
    }

    if (validationErrors.length > 0) {
      setBulkInviteErrors(validationErrors)
      return
    }

    try {
      await api.invitations.createBulk(parsedInvitations)
      setBulkInvites('')
      setInvitationMessage('')
      setInviteTab('list')
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send invitations')
    }
  }

  const handleResendInvitation = async (invitationId: number) => {
    setError('')
    try {
      await api.invitations.resend(invitationId)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend invitation')
    }
  }

  const handleRevokeInvitation = async (invitationId: number) => {
    if (!confirm('Revoke this invitation? The candidate will no longer be able to use it.')) {
      return
    }

    setError('')
    try {
      await api.invitations.revoke(invitationId)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to revoke invitation')
    }
  }

  const handlePreviewEmail = async () => {
    setPreviewError('')
    setPreviewLoading(true)

    try {
      const response = await api.invitations.preview(parseInt(id!), {
        candidate_name: inviteData.candidate_name || 'Candidate Name',
        custom_message: invitationMessage.trim() || undefined,
      })
      setEmailPreview(response.data)
    } catch (err: any) {
      setPreviewError(err.response?.data?.detail || 'Failed to load email preview')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleInviteTabSelect = (tabKey: string | null) => {
    const nextTab = tabKey || 'single'
    setInviteTab(nextTab)
    if (nextTab === 'preview') {
      handlePreviewEmail()
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
  const canActivate = (interview.questions?.length || 0) > 0
  
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
            <Button
              variant="success"
              onClick={handleActivate}
              disabled={!canActivate}
              title={!canActivate ? 'Add at least one question before activating' : undefined}
            >
              <FiActivity className="me-2" />
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

      {interview.status === 'draft' && !canActivate && (
        <Alert variant="warning">Add at least one question before activating this interview.</Alert>
      )}
      
      <Row>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Interview Details</h5>
                {interview.status === 'draft' && (
                  <Button
                    variant="outline-primary"
                    size="sm"
                    onClick={() => setIsEditingDetails((current) => !current)}
                  >
                    <FiEdit className="me-1" />
                    {isEditingDetails ? 'Cancel' : 'Edit'}
                  </Button>
                )}
              </div>
            </Card.Header>
            <Card.Body>
              {isEditingDetails ? (
                <Form onSubmit={handleUpdateDetails}>
                  <Form.Group className="mb-3" controlId="edit-interview-title">
                    <Form.Label>Title</Form.Label>
                    <Form.Control
                      value={editData.title}
                      onChange={(event) => setEditData({ ...editData, title: event.target.value })}
                      required
                    />
                  </Form.Group>
                  <Form.Group className="mb-3" controlId="edit-interview-description">
                    <Form.Label>Description</Form.Label>
                    <Form.Control
                      as="textarea"
                      rows={3}
                      value={editData.description}
                      onChange={(event) => setEditData({ ...editData, description: event.target.value })}
                    />
                  </Form.Group>
                  <Row>
                    <Col sm={6}>
                      <Form.Group className="mb-3" controlId="edit-interview-duration">
                        <Form.Label>Duration</Form.Label>
                        <Form.Control
                          type="number"
                          value={editData.duration_minutes}
                          onChange={(event) => setEditData({ ...editData, duration_minutes: parseInt(event.target.value) })}
                          min={5}
                          max={120}
                        />
                      </Form.Group>
                    </Col>
                    <Col sm={6}>
                      <Form.Group className="mb-3" controlId="edit-interview-attempts">
                        <Form.Label>Max Attempts</Form.Label>
                        <Form.Control
                          type="number"
                          value={editData.max_attempts}
                          onChange={(event) => setEditData({ ...editData, max_attempts: parseInt(event.target.value) })}
                          min={1}
                          max={10}
                        />
                      </Form.Group>
                    </Col>
                  </Row>
                  <Form.Group className="mb-3" controlId="edit-interview-pass-score">
                    <Form.Label>Pass Score</Form.Label>
                    <Form.Control
                      type="number"
                      value={editData.pass_score}
                      onChange={(event) => setEditData({ ...editData, pass_score: parseFloat(event.target.value) })}
                      min={0}
                      max={100}
                    />
                  </Form.Group>
                  <Button type="submit" size="sm">Save Details</Button>
                </Form>
              ) : (
                <>
                  <p><strong>Description:</strong> {interview.description || 'N/A'}</p>
                  <p><strong>Duration:</strong> {interview.duration_minutes} minutes</p>
                  <p><strong>Max Attempts:</strong> {interview.max_attempts}</p>
                  <p><strong>Pass Score:</strong> {interview.pass_score}%</p>
                  <p><strong>Created:</strong> {new Date(interview.created_at).toLocaleDateString()}</p>
                </>
              )}
            </Card.Body>
          </Card>
          
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Questions ({interview.questions?.length || 0})</h5>
                {interview.status === 'draft' && (
                  <Button
                    variant="outline-primary"
                    size="sm"
                    onClick={() => {
                      setQuestionDrafts(normalizeQuestions(interview.questions || []))
                      setIsEditingQuestions((current) => !current)
                    }}
                  >
                    <FiEdit className="me-1" />
                    {isEditingQuestions ? 'Cancel' : 'Edit'}
                  </Button>
                )}
              </div>
            </Card.Header>
            <Card.Body>
              {isEditingQuestions ? (
                <Form onSubmit={handleUpdateQuestions}>
                  {questionDrafts.map((question, questionIndex) => (
                    <Card key={questionIndex} className="mb-3 bg-light">
                      <Card.Body>
                        <div className="d-flex justify-content-between align-items-center mb-3">
                          <strong>Question {questionIndex + 1}</strong>
                          <Button type="button" size="sm" variant="outline-danger" onClick={() => removeQuestionDraft(questionIndex)} disabled={questionDrafts.length === 1}>
                            <FiTrash2 />
                          </Button>
                        </div>
                        <Form.Group className="mb-3" controlId={`edit-question-text-${questionIndex}`}>
                          <Form.Label>Question Text</Form.Label>
                          <Form.Control as="textarea" rows={2} value={question.question_text} onChange={(event) => updateQuestionDraft(questionIndex, 'question_text', event.target.value)} required />
                        </Form.Group>
                        <Form.Group className="mb-3" controlId={`edit-question-expected-${questionIndex}`}>
                          <Form.Label>Expected Answer</Form.Label>
                          <Form.Control as="textarea" rows={2} value={question.expected_answer} onChange={(event) => updateQuestionDraft(questionIndex, 'expected_answer', event.target.value)} />
                        </Form.Group>
                        <Form.Group className="mb-3" controlId={`edit-question-weight-${questionIndex}`}>
                          <Form.Label>Weight</Form.Label>
                          <Form.Control type="number" min={0.5} max={5} step={0.5} value={question.weight} onChange={(event) => updateQuestionDraft(questionIndex, 'weight', parseFloat(event.target.value))} />
                        </Form.Group>

                        <div className="d-flex justify-content-between align-items-center mb-2">
                          <small className="text-muted">Rubric Criteria</small>
                          <Button type="button" size="sm" variant="outline-secondary" onClick={() => addCriterionDraft(questionIndex)}>
                            <FiPlus className="me-1" />
                            Add Criterion
                          </Button>
                        </div>
                        {(question.rubric_criteria || []).map((criterion: any, criterionIndex: number) => (
                          <div key={criterionIndex} className="border rounded p-2 mb-2 bg-white">
                            <div className="d-flex justify-content-between align-items-center mb-2">
                              <strong className="small">Criterion {criterionIndex + 1}</strong>
                              <Button type="button" size="sm" variant="outline-danger" onClick={() => removeCriterionDraft(questionIndex, criterionIndex)}>
                                <FiTrash2 />
                              </Button>
                            </div>
                            <Form.Group className="mb-2" controlId={`edit-criterion-name-${questionIndex}-${criterionIndex}`}>
                              <Form.Label>Name</Form.Label>
                              <Form.Control value={criterion.name} onChange={(event) => updateCriterionDraft(questionIndex, criterionIndex, 'name', event.target.value)} />
                            </Form.Group>
                            <Form.Group className="mb-2" controlId={`edit-criterion-description-${questionIndex}-${criterionIndex}`}>
                              <Form.Label>Description</Form.Label>
                              <Form.Control as="textarea" rows={2} value={criterion.description} onChange={(event) => updateCriterionDraft(questionIndex, criterionIndex, 'description', event.target.value)} />
                            </Form.Group>
                            <Form.Group controlId={`edit-criterion-weight-${questionIndex}-${criterionIndex}`}>
                              <Form.Label>Weight</Form.Label>
                              <Form.Control type="number" min={0.5} max={5} step={0.5} value={criterion.weight} onChange={(event) => updateCriterionDraft(questionIndex, criterionIndex, 'weight', parseFloat(event.target.value))} />
                            </Form.Group>
                          </div>
                        ))}
                      </Card.Body>
                    </Card>
                  ))}
                  <div className="d-flex gap-2">
                    <Button type="button" size="sm" variant="outline-secondary" onClick={addQuestionDraft}>
                      <FiPlus className="me-1" />
                      Add Question
                    </Button>
                    <Button type="submit" size="sm">Save Questions</Button>
                  </div>
                </Form>
              ) : (
                interview.questions?.map((q: any, idx: number) => (
                  <div key={q.id} className="mb-3">
                    <strong>Q{idx + 1}:</strong> {q.question_text}
                    <br />
                    <small className="text-muted">Weight: {q.weight}x</small>
                    {(q.rubric_criteria || []).length > 0 && (
                      <div className="mt-2 ms-3">
                        <small className="text-muted d-block mb-1">Rubric criteria</small>
                        <ul className="mb-0">
                          {q.rubric_criteria.map((criterion: any) => (
                            <li key={criterion.id}>
                              <small>
                                <strong>{criterion.name}</strong>
                                {criterion.description ? `: ${criterion.description}` : ''}
                                {criterion.weight ? ` (${criterion.weight}x)` : ''}
                              </small>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))
              )}
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
                      <th>Actions</th>
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
                        <td>
                          <div className="d-flex gap-2">
                            <Button
                              size="sm"
                              variant="outline-primary"
                              onClick={() => handleResendInvitation(inv.id)}
                              disabled={inv.status === 'completed' || inv.status === 'revoked'}
                            >
                              Resend
                            </Button>
                            <Button
                              size="sm"
                              variant="outline-danger"
                              onClick={() => handleRevokeInvitation(inv.id)}
                              disabled={inv.status === 'completed' || inv.status === 'revoked'}
                            >
                              Revoke
                            </Button>
                          </div>
                        </td>
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
          <Tabs activeKey={inviteTab} onSelect={handleInviteTabSelect}>
            <Tab eventKey="single" title="Single Invite">
              <Form className="mt-3">
                <Form.Group className="mb-3" controlId="single-invite-candidate-name">
                  <Form.Label>Candidate Name</Form.Label>
                  <Form.Control
                    type="text"
                    value={inviteData.candidate_name}
                    onChange={(e) => setInviteData({...inviteData, candidate_name: e.target.value})}
                  />
                </Form.Group>
                <Form.Group className="mb-3" controlId="single-invite-candidate-email">
                  <Form.Label>Candidate Email</Form.Label>
                  <Form.Control
                    type="email"
                    value={inviteData.candidate_email}
                    onChange={(e) => setInviteData({...inviteData, candidate_email: e.target.value})}
                  />
                </Form.Group>
                <Form.Group className="mb-3" controlId="single-invite-message">
                  <Form.Label>Single Email Message</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={invitationMessage}
                    onChange={(e) => {
                      setInvitationMessage(e.target.value)
                      setEmailPreview(null)
                    }}
                    maxLength={1000}
                  />
                </Form.Group>
                <Button variant="primary" onClick={handleInvite}>
                  Send Invitation
                </Button>
              </Form>
            </Tab>
            <Tab eventKey="bulk" title="Bulk Invite">
              <Form className="mt-3">
                <Form.Group className="mb-3" controlId="bulk-invite-candidates">
                  <Form.Label>Enter candidates (one per line: email, name)</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={5}
                    value={bulkInvites}
                    onChange={(e) => {
                      setBulkInvites(e.target.value)
                      setBulkInviteErrors([])
                    }}
                    placeholder={"john@example.com, John Doe\njane@example.com, Jane Smith"}
                  />
                </Form.Group>
                {bulkInviteErrors.length > 0 && (
                  <Alert variant="danger">
                    <ul className="mb-0">
                      {bulkInviteErrors.map((validationError) => (
                        <li key={validationError}>{validationError}</li>
                      ))}
                    </ul>
                  </Alert>
                )}
                <Form.Group className="mb-3" controlId="bulk-invite-message">
                  <Form.Label>Bulk Email Message</Form.Label>
                  <Form.Control
                    as="textarea"
                    rows={3}
                    value={invitationMessage}
                    onChange={(e) => {
                      setInvitationMessage(e.target.value)
                      setEmailPreview(null)
                    }}
                    maxLength={1000}
                  />
                </Form.Group>
                <Button variant="primary" onClick={handleBulkInvite}>
                  Send All Invitations
                </Button>
              </Form>
            </Tab>
            <Tab eventKey="preview" title="Email Preview">
              <div className="mt-3">
                {previewError && <Alert variant="danger">{previewError}</Alert>}
                <Button variant="outline-primary" size="sm" onClick={handlePreviewEmail} disabled={previewLoading} className="mb-3">
                  {previewLoading ? 'Loading Preview...' : 'Refresh Preview'}
                </Button>
                {emailPreview && (
                  <>
                    <p><strong>Subject:</strong> {emailPreview.subject}</p>
                    <div className="border rounded bg-light p-3" data-testid="email-preview" dangerouslySetInnerHTML={{ __html: emailPreview.html_body }} />
                  </>
                )}
              </div>
            </Tab>
            <Tab eventKey="list" title="Sent Invitations">
              <Table size="sm" className="mt-3">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map(inv => (
                    <tr key={inv.id}>
                      <td>{inv.candidate_name}</td>
                      <td>{inv.candidate_email}</td>
                      <td><Badge bg="secondary">{inv.status}</Badge></td>
                      <td>
                        <Button
                          size="sm"
                          variant="outline-danger"
                          onClick={() => handleRevokeInvitation(inv.id)}
                          disabled={inv.status === 'completed' || inv.status === 'revoked'}
                        >
                          Revoke
                        </Button>
                      </td>
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
