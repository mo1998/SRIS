import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Table, Badge, Modal, Form, Alert, Tabs, Tab } from 'react-bootstrap'
import { useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { FiMail, FiDownload, FiEye, FiActivity, FiEdit, FiPlus, FiTrash2, FiXCircle } from 'react-icons/fi'
import { useRealTimeRefresh } from '../hooks/useRealTimeRefresh'

const MAX_BULK_INVITATIONS = 100

const InterviewDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()
  const [interview, setInterview] = useState<any>(null)
  const [responses, setResponses] = useState<any[]>([])
  const [evaluationAnalytics, setEvaluationAnalytics] = useState<any>(null)
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
  const [message, setMessage] = useState('')
  const [batchReevaluating, setBatchReevaluating] = useState(false)
  const [showComparisonModal, setShowComparisonModal] = useState(false)
  const [comparisonData, setComparisonData] = useState<any>(null)
  const [questionAnalytics, setQuestionAnalytics] = useState<any>(null)
  const [comparisonLoading, setComparisonLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadData()
  }, [id])
  
  const loadData = async () => {
    try {
      const [interviewRes, responsesRes, invitationsRes, analyticsRes] = await Promise.all([
        api.interviews.get(parseInt(id!)),
        api.responses.list(parseInt(id!)),
        api.invitations.list(parseInt(id!)),
        api.reports.getInterviewEvaluationAnalytics(parseInt(id!))
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
      setEvaluationAnalytics(analyticsRes.data)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
   }

   // Live-update when responses, evaluations, decisions, or interview status change.
   useRealTimeRefresh(loadData, [])

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
    if (!confirm(t('interviewDetail.activateConfirm'))) {
      return
    }
    
    try {
      await api.interviews.activate(parseInt(id!))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.activateFailed'))
    }
  }
  
  const handleComplete = async () => {
    if (!confirm(t('interviewDetail.completeConfirm'))) {
      return
    }
    
    try {
      await api.interviews.complete(parseInt(id!))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.completeFailed'))
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
      setError(err.response?.data?.detail || t('interviewDetail.updateFailed'))
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
      setError(err.response?.data?.detail || t('interviewDetail.questionsFailed'))
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
      setError(err.response?.data?.detail || t('interviewDetail.inviteFailed'))
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
        validationErrors.push(t('interviewDetail.rowOnlyEmailName', { row: rowNumber }))
        rowHasErrors = true
      }
      if (!email) {
        validationErrors.push(t('interviewDetail.rowEmailRequired', { row: rowNumber }))
        rowHasErrors = true
      } else if (!/^\S+@\S+\.\S+$/.test(email)) {
        validationErrors.push(t('interviewDetail.rowEmailInvalid', { row: rowNumber }))
        rowHasErrors = true
      } else if (seenEmails.has(email.toLowerCase())) {
        validationErrors.push(t('interviewDetail.rowDuplicate', { row: rowNumber }))
        rowHasErrors = true
      } else {
        seenEmails.add(email.toLowerCase())
      }
      if (!name) {
        validationErrors.push(t('interviewDetail.rowNameRequired', { row: rowNumber }))
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
      validationErrors.push(t('interviewDetail.addAtLeastOne'))
    }

    if (lines.length > MAX_BULK_INVITATIONS) {
      validationErrors.push(t('interviewDetail.bulkLimit', { count: MAX_BULK_INVITATIONS }))
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
      setError(err.response?.data?.detail || t('interviewDetail.bulkInviteFailed'))
    }
  }

  const handleResendInvitation = async (invitationId: number) => {
    setError('')
    try {
      await api.invitations.resend(invitationId)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.resendFailed'))
    }
  }

  const handleRevokeInvitation = async (invitationId: number) => {
    if (!confirm(t('interviewDetail.revokeConfirm'))) {
      return
    }

    setError('')
    try {
      await api.invitations.revoke(invitationId)
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.revokeFailed'))
    }
  }

  const handleCancelInvitation = async (invitationId: number) => {
    if (!confirm(t('interviewDetail.cancelConfirm'))) {
      return
    }

    setError('')
    try {
      await api.invitations.cancel(invitationId)
      setMessage(t('interviewDetail.invitationCancelled'))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.cancelFailed'))
    }
  }

  const handleCancelAllInvitations = async () => {
    if (!confirm(t('interviewDetail.cancelAllConfirm'))) {
      return
    }

    setError('')
    setMessage('')
    try {
      await api.invitations.cancelAll(parseInt(id!))
      setMessage(t('interviewDetail.invitationsCancelled'))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.cancelAllFailed'))
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
      setPreviewError(err.response?.data?.detail || t('interviewDetail.previewFailed'))
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

  const handleExportCsv = async () => {
    try {
      const response = await api.reports.exportInterviewCsv(parseInt(id!))
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `interview_${id}_responses.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to export CSV:', error)
    }
  }

  const handleShowComparison = async () => {
    setShowComparisonModal(true)
    setComparisonLoading(true)
    try {
      const [comparisonRes, analyticsRes] = await Promise.all([
        api.reports.getComparison(parseInt(id!)),
        api.reports.getQuestionAnalytics(parseInt(id!)),
      ])
      setComparisonData(comparisonRes.data)
      setQuestionAnalytics(analyticsRes.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.comparisonFailed'))
    } finally {
      setComparisonLoading(false)
    }
  }

  const handleBatchReevaluate = async () => {
    if (!confirm(t('interviewDetail.reevaluateConfirm'))) {
      return
    }

    setError('')
    setMessage('')
    setBatchReevaluating(true)
    try {
      const response = await api.reports.reevaluateInterview(parseInt(id!))
      setMessage(t('interviewDetail.queued', { count: response.data.length }))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.queueFailed'))
    } finally {
      setBatchReevaluating(false)
    }
  }

  const handleDeleteResponse = async (responseId: number) => {
    if (!confirm(t('interviewDetail.deleteResponseConfirm'))) {
      return
    }

    setError('')
    setMessage('')
    try {
      await api.responses.delete(responseId)
      setMessage(t('interviewDetail.responseDeleted'))
      loadData()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewDetail.deleteResponseFailed'))
    }
  }
  
  if (loading) {
    return <p>{t('interviewDetail.loading')}</p>
  }
  
  if (!interview) {
    return <p>{t('interviewDetail.notFound')}</p>
  }
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'draft': return <Badge bg="secondary">{t('interviewDetail.statusDraft')}</Badge>
      case 'active': return <Badge bg="success">{t('interviewDetail.statusActive')}</Badge>
      case 'completed': return <Badge bg="primary">{t('interviewDetail.statusCompleted')}</Badge>
      default: return <Badge bg="secondary">{status}</Badge>
    }
  }
  
  const sortedResponses = [...responses].sort((a, b) => (b.total_score || 0) - (a.total_score || 0))
  const canActivate = (interview.questions?.length || 0) > 0
  
  return (
    <div>
      {error && <Alert variant="danger">{error}</Alert>}
      {message && <Alert variant="success">{message}</Alert>}
      
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
              title={!canActivate ? t('interviewDetail.addQuestionFirst') : undefined}
            >
              <FiActivity className="me-2" />
              {t('interviewDetail.activate')}
            </Button>
          )}
          {interview.status === 'active' && (
            <Button variant="warning" onClick={handleComplete}>
              {t('interviewDetail.complete')}
            </Button>
          )}
          <Button variant="outline-primary" onClick={() => setShowInviteModal(true)}>
            <FiMail className="me-2" />
            {t('interviewDetail.inviteCandidates')}
          </Button>
          {responses.length > 0 && (
            <Button variant="outline-dark" onClick={handleDownloadReport}>
              <FiDownload className="me-2" />
              {t('interviewDetail.downloadReport')}
            </Button>
          )}
          {responses.some((response) => response.status === 'completed') && (
            <Button variant="outline-primary" onClick={handleBatchReevaluate} disabled={batchReevaluating}>
              {batchReevaluating ? t('interviewDetail.queueing') : t('interviewDetail.reevaluateAll')}
            </Button>
          )}
          {responses.some((response) => response.status === 'completed') && (
            <Button variant="outline-primary" onClick={handleShowComparison}>
              <FiActivity className="me-2" />
              {t('interviewDetail.compare')}
            </Button>
          )}
          {responses.length > 0 && (
            <Button variant="outline-dark" onClick={handleExportCsv}>
              <FiDownload className="me-2" />
              {t('interviewDetail.exportCsv')}
            </Button>
          )}
        </div>
      </div>

      {interview.status === 'draft' && !canActivate && (
        <Alert variant="warning">{t('interviewDetail.addQuestionBeforeActivate')}</Alert>
      )}
      
      <Row>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">{t('interviewDetail.details')}</h5>
                {interview.status === 'draft' && (
                  <Button
                    variant="outline-primary"
                    size="sm"
                    onClick={() => setIsEditingDetails((current) => !current)}
                  >
                    <FiEdit className="me-1" />
                    {isEditingDetails ? t('interviewDetail.cancel') : t('interviewDetail.edit')}
                  </Button>
                )}
              </div>
            </Card.Header>
            <Card.Body>
              {isEditingDetails ? (
                <Form onSubmit={handleUpdateDetails}>
                  <Form.Group className="mb-3" controlId="edit-interview-title">
                    <Form.Label>{t('common.title')}</Form.Label>
                    <Form.Control
                      value={editData.title}
                      onChange={(event) => setEditData({ ...editData, title: event.target.value })}
                      required
                    />
                  </Form.Group>
                  <Form.Group className="mb-3" controlId="edit-interview-description">
                    <Form.Label>{t('common.description')}</Form.Label>
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
                        <Form.Label>{t('dashboard.duration')}</Form.Label>
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
                        <Form.Label>{t('interviewDetail.maxAttempts')}</Form.Label>
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
                    <Form.Label>{t('interviewDetail.passScore')}</Form.Label>
                    <Form.Control
                      type="number"
                      value={editData.pass_score}
                      onChange={(event) => setEditData({ ...editData, pass_score: parseFloat(event.target.value) })}
                      min={0}
                      max={100}
                    />
                  </Form.Group>
                  <Button type="submit" size="sm">{t('interviewDetail.saveDetails')}</Button>
                </Form>
              ) : (
                <>
                  <p><strong>{t('common.description')}:</strong> {interview.description || t('common.n/a')}</p>
                  <p><strong>{t('dashboard.duration')}:</strong> {t('interviewDetail.minutes', { count: interview.duration_minutes })}</p>
                  <p><strong>{t('interviewDetail.maxAttempts')}:</strong> {interview.max_attempts}</p>
                  <p><strong>{t('interviewDetail.passScore')}:</strong> {interview.pass_score}%</p>
                  <p><strong>{t('dashboard.created')}:</strong> {new Date(interview.created_at).toLocaleDateString()}</p>
                </>
              )}
            </Card.Body>
          </Card>
          
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">{t('interviewDetail.questionsCount', { count: interview.questions?.length || 0 })}</h5>
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
                    {isEditingQuestions ? t('interviewDetail.cancel') : t('interviewDetail.edit')}
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
                          <strong>{t('interviewDetail.questionN', { n: questionIndex + 1 })}</strong>
                          <Button type="button" size="sm" variant="outline-danger" onClick={() => removeQuestionDraft(questionIndex)} disabled={questionDrafts.length === 1}>
                            <FiTrash2 />
                          </Button>
                        </div>
                        <Form.Group className="mb-3" controlId={`edit-question-text-${questionIndex}`}>
                          <Form.Label>{t('interviewDetail.questionText')}</Form.Label>
                          <Form.Control as="textarea" rows={2} value={question.question_text} onChange={(event) => updateQuestionDraft(questionIndex, 'question_text', event.target.value)} required />
                        </Form.Group>
                        <Form.Group className="mb-3" controlId={`edit-question-expected-${questionIndex}`}>
                          <Form.Label>{t('interviewDetail.expectedAnswer')}</Form.Label>
                          <Form.Control as="textarea" rows={2} value={question.expected_answer} onChange={(event) => updateQuestionDraft(questionIndex, 'expected_answer', event.target.value)} />
                        </Form.Group>
                        <Form.Group className="mb-3" controlId={`edit-question-weight-${questionIndex}`}>
                          <Form.Label>{t('common.weight')}</Form.Label>
                          <Form.Control type="number" min={0.5} max={5} step={0.5} value={question.weight} onChange={(event) => updateQuestionDraft(questionIndex, 'weight', parseFloat(event.target.value))} />
                        </Form.Group>

                        <div className="d-flex justify-content-between align-items-center mb-2">
                          <small className="text-muted">{t('interviewDetail.rubricCriteria')}</small>
                          <Button type="button" size="sm" variant="outline-secondary" onClick={() => addCriterionDraft(questionIndex)}>
                            <FiPlus className="me-1" />
                            {t('interviewDetail.addCriterion')}
                          </Button>
                        </div>
                        {(question.rubric_criteria || []).map((criterion: any, criterionIndex: number) => (
                          <div key={criterionIndex} className="border rounded p-2 mb-2 bg-white">
                            <div className="d-flex justify-content-between align-items-center mb-2">
                              <strong className="small">{t('interviewDetail.criterionN', { n: criterionIndex + 1 })}</strong>
                              <Button type="button" size="sm" variant="outline-danger" onClick={() => removeCriterionDraft(questionIndex, criterionIndex)}>
                                <FiTrash2 />
                              </Button>
                            </div>
                            <Form.Group className="mb-2" controlId={`edit-criterion-name-${questionIndex}-${criterionIndex}`}>
                              <Form.Label>{t('common.name')}</Form.Label>
                              <Form.Control value={criterion.name} onChange={(event) => updateCriterionDraft(questionIndex, criterionIndex, 'name', event.target.value)} />
                            </Form.Group>
                            <Form.Group className="mb-2" controlId={`edit-criterion-description-${questionIndex}-${criterionIndex}`}>
                              <Form.Label>{t('common.description')}</Form.Label>
                              <Form.Control as="textarea" rows={2} value={criterion.description} onChange={(event) => updateCriterionDraft(questionIndex, criterionIndex, 'description', event.target.value)} />
                            </Form.Group>
                            <Form.Group controlId={`edit-criterion-weight-${questionIndex}-${criterionIndex}`}>
                              <Form.Label>{t('common.weight')}</Form.Label>
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
                      {t('interviewDetail.addQuestion')}
                    </Button>
                    <Button type="submit" size="sm">{t('interviewDetail.saveQuestions')}</Button>
                  </div>
                </Form>
              ) : (
                interview.questions?.map((q: any, idx: number) => (
                  <div key={q.id} className="mb-3">
                    <strong>{t('interviewDetail.questionShort', { n: idx + 1 })}</strong> {q.question_text}
                    <br />
                    <small className="text-muted">{t('interviewDetail.weightX', { weight: q.weight })}</small>
                    {(q.rubric_criteria || []).length > 0 && (
                      <div className="mt-2 ms-3">
                        <small className="text-muted d-block mb-1">{t('interviewDetail.rubricCriteriaSmall')}</small>
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
              <h5 className="mb-0">{t('interviewDetail.candidateResponses', { count: responses.length })}</h5>
            </Card.Header>
            <Card.Body>
              {evaluationAnalytics && (
                <Row className="mb-3">
                  <Col md={3}>
                    <strong>{t('interviewDetail.evalRuns')}</strong>
                    <p className="mb-0">{evaluationAnalytics.total_evaluation_runs}</p>
                  </Col>
                  <Col md={3}>
                    <strong>{t('common.completed')}</strong>
                    <p className="mb-0">{evaluationAnalytics.completed_runs}</p>
                  </Col>
                  <Col md={3}>
                    <strong>{t('interviewDetail.avgLatest')}</strong>
                    <p className="mb-0">{evaluationAnalytics.average_latest_score.toFixed(1)}%</p>
                  </Col>
                  <Col md={3}>
                    <strong>{t('interviewDetail.fallbacks')}</strong>
                    <p className="mb-0">{evaluationAnalytics.fallback_count}</p>
                  </Col>
                </Row>
              )}
              {responses.length === 0 ? (
                <p className="text-center text-muted">{t('interviewDetail.noResponses')}</p>
              ) : (
                <Table striped bordered hover responsive>
                  <thead>
                    <tr>
                      <th>{t('interviewDetail.rank')}</th>
                      <th>{t('common.name')}</th>
                      <th>{t('common.email')}</th>
                      <th>{t('common.score')}</th>
                      <th>{t('common.status')}</th>
                      <th>{t('interviewDetail.confidence')}</th>
                      <th>{t('common.actions')}</th>
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
                        <td>{response.confidence_score?.toFixed(1) || t('common.n/a')}%</td>
                        <td>
                          <div className="d-flex gap-2">
                            <Link to={`/employer/candidate/${response.id}`}>
                              <Button variant="outline-primary" size="sm">
                                <FiEye /> {t('interviewDetail.viewReport')}
                              </Button>
                            </Link>
                            <Button variant="outline-danger" size="sm" onClick={() => handleDeleteResponse(response.id)}>
                              <FiTrash2 /> {t('common.delete')}
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
          
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">{t('interviewDetail.invitations', { count: invitations.length })}</h5>
                {invitations.some((inv) => inv.status === 'completed') && (
                  <Button size="sm" variant="outline-danger" onClick={handleCancelAllInvitations}>
                    <FiXCircle className="me-1" />
                    {t('interviewDetail.cancelAll')}
                  </Button>
                )}
              </div>
            </Card.Header>
            <Card.Body>
              {invitations.length === 0 ? (
                <p className="text-muted">{t('interviewDetail.noInvitations')}</p>
              ) : (
                <Table size="sm">
                  <thead>
                    <tr>
                      <th>{t('common.name')}</th>
                      <th>{t('common.email')}</th>
                      <th>{t('common.status')}</th>
                      <th>{t('interviewDetail.sent')}</th>
                      <th>{t('common.actions')}</th>
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
                        <td>{inv.sent_at ? new Date(inv.sent_at).toLocaleDateString() : t('interviewDetail.notSent')}</td>
                        <td>
                          <div className="d-flex gap-2">
                            {inv.status === 'completed' ? (
                              <Button
                                size="sm"
                                variant="outline-danger"
                                onClick={() => handleCancelInvitation(inv.id)}
                              >
                                <FiXCircle className="me-1" />
                                {t('interviewDetail.cancelInvitation')}
                              </Button>
                            ) : (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline-primary"
                                  onClick={() => handleResendInvitation(inv.id)}
                                  disabled={inv.status === 'revoked'}
                                >
                                  {t('interviewDetail.resend')}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline-danger"
                                  onClick={() => handleRevokeInvitation(inv.id)}
                                  disabled={inv.status === 'revoked'}
                                >
                                  {t('interviewDetail.revoke')}
                                </Button>
                              </>
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
        </Col>
      </Row>
      
      {/* Invite Modal */}
      <Modal show={showInviteModal} onHide={() => setShowInviteModal(false)}>
        <Modal.Header closeButton>
          <Modal.Title>{t('interviewDetail.inviteTitle')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Tabs activeKey={inviteTab} onSelect={handleInviteTabSelect}>
            <Tab eventKey="single" title={t('interviewDetail.singleInvite')}>
              <Form className="mt-3">
                <Form.Group className="mb-3" controlId="single-invite-candidate-name">
                  <Form.Label>{t('interviewDetail.candidateName')}</Form.Label>
                  <Form.Control
                    type="text"
                    value={inviteData.candidate_name}
                    onChange={(e) => setInviteData({...inviteData, candidate_name: e.target.value})}
                  />
                </Form.Group>
                <Form.Group className="mb-3" controlId="single-invite-candidate-email">
                  <Form.Label>{t('interviewDetail.candidateEmail')}</Form.Label>
                  <Form.Control
                    type="email"
                    value={inviteData.candidate_email}
                    onChange={(e) => setInviteData({...inviteData, candidate_email: e.target.value})}
                  />
                </Form.Group>
                <Form.Group className="mb-3" controlId="single-invite-message">
                  <Form.Label>{t('interviewDetail.singleMessage')}</Form.Label>
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
                  {t('interviewDetail.sendInvitation')}
                </Button>
              </Form>
            </Tab>
            <Tab eventKey="bulk" title={t('interviewDetail.bulkInvite')}>
              <Form className="mt-3">
                <Form.Group className="mb-3" controlId="bulk-invite-candidates">
                  <Form.Label>{t('interviewDetail.bulkCandidates')}</Form.Label>
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
                  <Form.Label>{t('interviewDetail.bulkMessage')}</Form.Label>
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
                  {t('interviewDetail.sendAll')}
                </Button>
              </Form>
            </Tab>
            <Tab eventKey="preview" title={t('interviewDetail.emailPreview')}>
              <div className="mt-3">
                {previewError && <Alert variant="danger">{previewError}</Alert>}
                <Button variant="outline-primary" size="sm" onClick={handlePreviewEmail} disabled={previewLoading} className="mb-3">
                  {previewLoading ? t('interviewDetail.loadingPreview') : t('interviewDetail.refreshPreview')}
                </Button>
                {emailPreview && (
                  <>
                    <p><strong>{t('interviewDetail.subject')}</strong> {emailPreview.subject}</p>
                    <div className="border rounded bg-light p-3" data-testid="email-preview" dangerouslySetInnerHTML={{ __html: emailPreview.html_body }} />
                  </>
                )}
              </div>
            </Tab>
            <Tab eventKey="list" title={t('interviewDetail.sentInvitations')}>
              <Table size="sm" className="mt-3">
                <thead>
                  <tr>
                    <th>{t('common.name')}</th>
                    <th>{t('common.email')}</th>
                    <th>{t('common.status')}</th>
                    <th>{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map(inv => (
                    <tr key={inv.id}>
                      <td>{inv.candidate_name}</td>
                      <td>{inv.candidate_email}</td>
                      <td><Badge bg="secondary">{inv.status}</Badge></td>
                      <td>
                        <div className="d-flex gap-2">
                          {inv.status === 'completed' ? (
                            <Button
                              size="sm"
                              variant="outline-danger"
                              onClick={() => handleCancelInvitation(inv.id)}
                            >
                              <FiXCircle className="me-1" />
                              {t('interviewDetail.cancelInvitation')}
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline-danger"
                              onClick={() => handleRevokeInvitation(inv.id)}
                              disabled={inv.status === 'revoked'}
                            >
                              {t('interviewDetail.revoke')}
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </Tab>
          </Tabs>
        </Modal.Body>
      </Modal>

      {/* Comparison Modal */}
      <Modal show={showComparisonModal} onHide={() => setShowComparisonModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>{t('interviewDetail.comparison')}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          {comparisonLoading ? (
            <p className="text-center text-muted">{t('interviewDetail.loadingComparison')}</p>
          ) : comparisonData ? (
            <>
              <Table striped bordered hover responsive size="sm">
                <thead>
                  <tr>
                    <th>{t('interviewDetail.candidate')}</th>
                    <th>{t('interviewDetail.overallScore')}</th>
                    <th>{t('interviewDetail.passFail')}</th>
                    <th>{t('interviewDetail.questions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonData.candidates?.map((candidate: any) => (
                    <tr key={candidate.response_id}>
                      <td>
                        <Link to={`/employer/candidate/${candidate.response_id}`}>
                          {candidate.candidate_name}
                        </Link>
                      </td>
                      <td>
                        <Badge bg={candidate.total_score >= (interview?.pass_score || 70) ? 'success' : 'danger'}>
                          {candidate.total_score?.toFixed(1) || 0}%
                        </Badge>
                      </td>
                      <td>
                        <Badge bg={candidate.passed ? 'success' : 'danger'}>
                          {candidate.passed ? t('interviewDetail.pass') : t('interviewDetail.fail')}
                        </Badge>
                      </td>
                      <td>
                        <Table size="sm" className="mb-0">
                          <thead>
                            <tr>
                              {candidate.question_scores?.map((answer: any, i: number) => (
                                <th key={i}>{answer.question.length > 12 ? `${answer.question.slice(0, 12)}...` : answer.question}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            <tr>
                              {candidate.question_scores?.map((answer: any, i: number) => (
                                <td key={i}>
                                  <Badge bg={answer.score === null ? 'light' : answer.score >= 70 ? 'success' : answer.score >= 50 ? 'warning' : 'danger'}>
                                    {answer.score === null ? t('common.n/a') : `${answer.score.toFixed(0)}%`}
                                  </Badge>
                                </td>
                              ))}
                            </tr>
                          </tbody>
                        </Table>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>

              {questionAnalytics && questionAnalytics.questions?.length > 0 && (
                <>
                  <hr />
                  <h6>{t('interviewDetail.questionAnalytics')}</h6>
                  <Table striped bordered hover responsive size="sm">
                    <thead>
                      <tr>
                        <th>{t('interviewDetail.question')}</th>
                        <th>{t('interviewDetail.responses')}</th>
                        <th>{t('interviewDetail.avgScore')}</th>
                        <th>{t('interviewDetail.difficulty')}</th>
                        <th>{t('interviewDetail.discrimination')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {questionAnalytics.questions.map((q: any, i: number) => (
                        <tr key={i}>
                          <td>{q.question}</td>
                          <td>{q.response_count}</td>
                          <td>{q.average_score?.toFixed(1)}%</td>
                          <td>
                            <Badge bg={q.difficulty === 'hard' ? 'danger' : q.difficulty === 'medium' ? 'warning' : 'success'}>
                              {q.difficulty}
                            </Badge>
                          </td>
                          <td>{q.discrimination?.toFixed(2) ?? t('common.n/a')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </>
              )}
            </>
          ) : (
            <p className="text-center text-muted">{t('interviewDetail.noComparison')}</p>
          )}
        </Modal.Body>
      </Modal>
    </div>
  )
}

export default InterviewDetail
