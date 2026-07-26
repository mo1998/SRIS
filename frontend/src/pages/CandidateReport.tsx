import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Badge, Button, Table, Accordion } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../store/authStore'
import { FiArrowLeft, FiDownload } from 'react-icons/fi'
import InterviewFeedbackCard from '../components/ui/InterviewFeedbackCard'

const CandidateReport: React.FC = () => {
  const { responseId } = useParams<{ responseId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [report, setReport] = useState<any>(null)
  const [evaluationAudit, setEvaluationAudit] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [reevaluating, setReevaluating] = useState(false)
  const [reevaluationError, setReevaluationError] = useState('')
  
  useEffect(() => {
    loadReport()
  }, [responseId])
  
  const loadReport = async () => {
    try {
      const parsedResponseId = parseInt(responseId!)
      const [reportResponse, auditResponse] = await Promise.all([
        api.reports.getCandidateReport(parsedResponseId),
        api.reports.getCandidateEvaluations(parsedResponseId),
      ])
      setReport(reportResponse.data)
      setEvaluationAudit(auditResponse.data)
    } catch (error) {
      console.error('Failed to load report:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const handleDownloadPdf = async () => {
    try {
      const response = await api.reports.downloadCandidatePdf(parseInt(responseId!))
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `candidate_${responseId}_report.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to download PDF:', error)
    }
  }

  const handleReevaluate = async () => {
    if (!window.confirm('Run a new evaluation for this response? This will create a new audit run.')) {
      return
    }

    setReevaluationError('')
    setReevaluating(true)

    try {
      await api.reports.reevaluateCandidate(parseInt(responseId!))
      await loadReport()
    } catch (error: any) {
      setReevaluationError(error.response?.data?.detail || 'Failed to re-evaluate response')
    } finally {
      setReevaluating(false)
    }
  }
  
  if (loading) {
    return <p>Loading report...</p>
  }
  
  if (!report) {
    return <p>Report not found</p>
  }
  
  const getScoreClass = (score: number) => {
    if (score >= 80) return 'score-high'
    if (score >= 60) return 'score-medium'
    return 'score-low'
  }

  const getEmotionClass = (emotion: string) => {
    return `emotion-${emotion.toLowerCase()}`
  }

  const formatDateTime = (value?: string) => {
    if (!value) return 'N/A'
    return new Date(value).toLocaleString()
  }

  const getRunScore = (run: any) => {
    const summaryScore = Number(run.raw_summary?.total_score)
    if (!Number.isNaN(summaryScore)) return summaryScore
    if (!run.scores?.length) return 0
    return run.scores.reduce((total: number, score: any) => total + Number(score.score || 0), 0) / run.scores.length
  }

  const formatScoreDelta = (run: any, previousRun?: any) => {
    if (!previousRun) return 'Baseline'
    const delta = getRunScore(run) - getRunScore(previousRun)
    if (delta === 0) return 'No change'
    return `${delta > 0 ? '+' : ''}${delta.toFixed(1)} pts`
  }

  const canManageEvaluations = user?.role === 'employer' || user?.role === 'admin'
  
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <Button variant="outline-secondary" onClick={() => navigate(-1)}>
          <FiArrowLeft className="me-2" />
          Back
        </Button>
        <Button variant="outline-primary" onClick={handleDownloadPdf}>
          <FiDownload className="me-2" />
          Download PDF
        </Button>
      </div>
      {reevaluationError && <p className="text-danger">{reevaluationError}</p>}
      
      <Card className="mb-4">
        <Card.Header>
          <h4 className="mb-0">Candidate Performance Report</h4>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <h5>Candidate Information</h5>
              <p><strong>Name:</strong> {report.candidate_name}</p>
              <p><strong>Email:</strong> {report.candidate_email}</p>
              <p><strong>Interview:</strong> {report.interview_title}</p>
            </Col>
            <Col md={6} className="text-center">
              <h5>Overall Score</h5>
              <div className={`score-circle ${getScoreClass(report.total_score)}`}>
                {report.total_score.toFixed(1)}%
              </div>
              <Badge bg={report.passed ? 'success' : 'danger'} className="mt-2" style={{ fontSize: '16px' }}>
                {report.passed ? 'PASSED' : 'FAILED'}
              </Badge>
            </Col>
          </Row>
          {(report.evaluation_provider || report.evaluation_model) && (
            <div className="border-top mt-3 pt-3">
              <h6>Evaluation Agent</h6>
              <p className="mb-1"><strong>Provider:</strong> {report.evaluation_provider || 'N/A'}</p>
              <p className="mb-1"><strong>Model:</strong> {report.evaluation_model || 'N/A'}</p>
              <p className="mb-0"><strong>Status:</strong> {report.evaluation_status || 'N/A'}</p>
            </div>
          )}
        </Card.Body>
      </Card>
      
      <Row>
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">Environment Quality</h6>
            </Card.Header>
            <Card.Body>
              <Table bordered>
                <tbody>
                  <tr>
                    <td>Voice Quality</td>
                    <td>
                      <Badge bg={report.voice_quality >= 80 ? 'success' : report.voice_quality >= 60 ? 'warning' : 'danger'}>
                        {report.voice_quality.toFixed(1)}%
                      </Badge>
                    </td>
                  </tr>
                  <tr>
                    <td>Background Quality</td>
                    <td>
                      <Badge bg={report.background_quality >= 80 ? 'success' : report.background_quality >= 60 ? 'warning' : 'danger'}>
                        {report.background_quality.toFixed(1)}%
                      </Badge>
                    </td>
                  </tr>
                  <tr>
                    <td>Face Visibility</td>
                    <td>
                      <Badge bg={report.face_visibility >= 80 ? 'success' : report.face_visibility >= 60 ? 'warning' : 'danger'}>
                        {report.face_visibility.toFixed(1)}%
                      </Badge>
                    </td>
                  </tr>
                  <tr>
                    <td>Lighting</td>
                    <td>
                      <Badge bg={report.lighting >= 80 ? 'success' : report.lighting >= 60 ? 'warning' : 'danger'}>
                        {report.lighting.toFixed(1)}%
                      </Badge>
                    </td>
                  </tr>
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">Emotion & Confidence Analysis</h6>
            </Card.Header>
            <Card.Body className="text-center">
              <Row>
                <Col>
                  <h5>Dominant Emotion</h5>
                  <span className={`emotion-badge ${getEmotionClass(report.dominant_emotion)}`}>
                    {report.dominant_emotion}
                  </span>
                </Col>
                <Col>
                  <h5>Confidence Score</h5>
                  <div className={`score-circle ${getScoreClass(report.confidence_score)}`} style={{ width: '80px', height: '80px', fontSize: '18px' }}>
                    {report.confidence_score.toFixed(1)}%
                  </div>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Card className="border-0">
        <Card.Header className="bg-transparent px-0 pt-0 border-bottom-0">
          <h5 className="mb-0 fw-semibold">Question-by-Question Breakdown</h5>
        </Card.Header>
        <Card.Body className="px-0 pb-0">
          {report.answers.map((answer: any, idx: number) => (
            <InterviewFeedbackCard
              key={idx}
              questionNumber={idx + 1}
              questionText={answer.question || `Question ${idx + 1}`}
              expectedAnswer={answer.expected_answer}
              answerText={answer.answer_text}
              score={answer.score ?? 0}
              emotion={answer.emotion}
              feedbackEn={answer.feedback_en || answer.feedback}
              feedbackAr={answer.feedback_ar}
              evidence={answer.evidence}
            />
          ))}
        </Card.Body>
      </Card>

      <Card className="mt-4 border-0">
        <Card.Header className="bg-transparent px-0 pt-0 border-bottom-0">
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0 fw-semibold">Evaluation Audit Trail</h5>
            {canManageEvaluations && (
              <Button variant="outline-primary" size="sm" onClick={handleReevaluate} disabled={reevaluating}>
                {reevaluating ? 'Re-evaluating...' : 'Re-evaluate'}
              </Button>
            )}
          </div>
        </Card.Header>
        <Card.Body className="px-0">
          {evaluationAudit.length === 0 ? (
            <p className="text-muted mb-0">No evaluation runs recorded.</p>
          ) : (
            <Accordion defaultActiveKey="0">
              {evaluationAudit.map((run: any, runIndex: number) => (
                <Accordion.Item eventKey={`${runIndex}`} key={run.id}>
                  <Accordion.Header>
                    <span className="me-2">Run #{run.id}</span>
                    {runIndex === 0 && <Badge bg="primary" className="me-2">Latest</Badge>}
                    <Badge bg={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : 'warning'}>
                      {run.status}
                    </Badge>
                  </Accordion.Header>
                  <Accordion.Body>
                    <Row className="mb-4 g-3">
                      <Col md={6}>
                        <p className="mb-1"><strong>Provider:</strong> {run.provider}</p>
                        <p className="mb-1"><strong>Model:</strong> {run.model_name || 'N/A'}</p>
                        <p className="mb-1"><strong>Config Hash:</strong> {run.config_hash || 'N/A'}</p>
                      </Col>
                      <Col md={6}>
                        <p className="mb-1"><strong>Started:</strong> {formatDateTime(run.started_at)}</p>
                        <p className="mb-1"><strong>Completed:</strong> {formatDateTime(run.completed_at)}</p>
                        <p className="mb-1"><strong>Score Delta:</strong> {formatScoreDelta(run, evaluationAudit[runIndex + 1])}</p>
                        {run.raw_summary && (
                          <p className="mb-1"><strong>Summary:</strong> {run.raw_summary.total_score?.toFixed?.(1) || run.raw_summary.total_score || 0}% / {run.raw_summary.answer_count || 0} answers</p>
                        )}
                      </Col>
                    </Row>
                    {run.error && <p className="text-danger"><strong>Error:</strong> {run.error}</p>}
                    {run.scores.map((score: any, sIdx: number) => (
                      <InterviewFeedbackCard
                        key={score.id}
                        questionNumber={sIdx + 1}
                        questionText={score.question || `Question ${score.question_id}`}
                        score={score.score}
                        feedbackEn={score.feedback_en}
                        feedbackAr={score.feedback_ar}
                        evidence={score.evidence}
                      />
                    ))}
                  </Accordion.Body>
                </Accordion.Item>
              ))}
            </Accordion>
          )}
        </Card.Body>
      </Card>
    </div>
  )
}

export default CandidateReport
