import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Badge, Button, Table, Accordion } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../store/authStore'
import { FiArrowLeft, FiDownload } from 'react-icons/fi'
import InterviewFeedbackCard from '../components/ui/InterviewFeedbackCard'

const CandidateReport: React.FC = () => {
  const { t } = useTranslation()
  const { responseId } = useParams<{ responseId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [report, setReport] = useState<any>(null)
  const [evaluationAudit, setEvaluationAudit] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [reevaluating, setReevaluating] = useState(false)
  const [reevaluationError, setReevaluationError] = useState('')
  const canManageEvaluations = user?.role === 'employer' || user?.role === 'admin'
  const isEmployerView = canManageEvaluations
  
  useEffect(() => {
    loadReport()
  }, [responseId])
  
  const loadReport = async () => {
    try {
      const parsedResponseId = parseInt(responseId!)
      const reportPromise = api.reports.getCandidateReport(parsedResponseId)
      const auditPromise = canManageEvaluations
        ? api.reports.getCandidateEvaluations(parsedResponseId)
        : Promise.resolve({ data: [] as any[] })
      const [reportResponse, auditResponse] = await Promise.all([reportPromise, auditPromise])
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
    if (!window.confirm(t('candidateReport.reevaluateConfirm'))) {
      return
    }

    setReevaluationError('')
    setReevaluating(true)

    try {
      await api.reports.reevaluateCandidate(parseInt(responseId!))
      await loadReport()
    } catch (error: any) {
      setReevaluationError(error.response?.data?.detail || t('candidateReport.reevaluateFailed'))
    } finally {
      setReevaluating(false)
    }
  }
  
  if (loading) {
    return <p>{t('candidateReport.loading')}</p>
  }
  
  if (!report) {
    return <p>{t('candidateReport.notFound')}</p>
  }
  
  const getScoreClass = (score: number) => {
    if (score >= 80) return 'score-high'
    if (score >= 60) return 'score-medium'
    return 'score-low'
  }

  const getEmotionClass = (emotion?: string) => {
    return emotion ? `emotion-${emotion.toLowerCase()}` : 'emotion-unknown'
  }

  const formatPercent = (value?: number | null) => {
    if (value === null || value === undefined || Number.isNaN(value)) return t('common.n/a')
    return `${value.toFixed(1)}%`
  }

  const qualityBadge = (value?: number | null) => {
    if (value === null || value === undefined) {
      return <Badge bg="secondary">{t('candidateReport.noQualityData')}</Badge>
    }
    return (
      <Badge bg={value >= 80 ? 'success' : value >= 60 ? 'warning' : 'danger'}>
        {value.toFixed(1)}%
      </Badge>
    )
  }

  const emotionDistribution = (): { emotion: string; count: number }[] => {
    if (!report?.answers) return []
    const counts = new Map<string, number>()
    for (const answer of report.answers) {
      const emotion = answer?.emotion
      if (!emotion) continue
      counts.set(emotion, (counts.get(emotion) || 0) + 1)
    }
    return [...counts.entries()]
      .map(([emotion, count]) => ({ emotion, count }))
      .sort((a, b) => b.count - a.count)
  }
  const distribution = emotionDistribution()
  const emotionSampleCount = distribution.reduce((sum, d) => sum + d.count, 0)

  const formatDateTime = (value?: string) => {
    if (!value) return t('common.n/a')
    return new Date(value).toLocaleString()
  }

  const getRunScore = (run: any) => {
    const summaryScore = Number(run.raw_summary?.total_score)
    if (!Number.isNaN(summaryScore)) return summaryScore
    if (!run.scores?.length) return 0
    return run.scores.reduce((total: number, score: any) => total + Number(score.score || 0), 0) / run.scores.length
  }

  const formatScoreDelta = (run: any, previousRun?: any) => {
    if (!previousRun) return t('candidateReport.baseline')
    const delta = getRunScore(run) - getRunScore(previousRun)
    if (delta === 0) return t('candidateReport.noChange')
    return `${delta > 0 ? '+' : ''}${delta.toFixed(1)} pts`
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <Button variant="outline-secondary" onClick={() => navigate(-1)}>
          <FiArrowLeft className="me-2" />
          {t('candidateReport.back')}
        </Button>
        <Button variant="outline-primary" onClick={handleDownloadPdf}>
          <FiDownload className="me-2" />
          {t('candidateReport.downloadPdf')}
        </Button>
      </div>
      {reevaluationError && <p className="text-danger">{reevaluationError}</p>}
      
      <Card className="mb-4">
        <Card.Header>
          <h4 className="mb-0">{t('candidateReport.title')}</h4>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <h5>{t('candidateReport.candidateInformation')}</h5>
              <p><strong>{t('candidateReport.name')}:</strong> {report.candidate_name}</p>
              <p><strong>{t('candidateReport.email')}:</strong> {report.candidate_email}</p>
              <p><strong>{t('candidateReport.interview')}:</strong> {report.interview_title}</p>
            </Col>
            <Col md={6} className="text-center">
              <h5>{t('candidateReport.overallScore')}</h5>
              <div className={`score-circle ${getScoreClass(report.total_score)}`}>
                {formatPercent(report.total_score)}
              </div>
              <Badge bg={report.passed ? 'success' : 'danger'} className="mt-2" style={{ fontSize: '16px' }}>
                {report.passed ? t('candidateReport.passed') : t('candidateReport.failed')}
              </Badge>
            </Col>
          </Row>
          {isEmployerView && (report.evaluation_provider || report.evaluation_model) && (
            <div className="border-top mt-3 pt-3">
              <h6>{t('candidateReport.evaluationAgent')}</h6>
              <p className="mb-1"><strong>{t('candidateReport.provider')}:</strong> {report.evaluation_provider || t('common.n/a')}</p>
              <p className="mb-1"><strong>{t('candidateReport.model')}:</strong> {report.evaluation_model || t('common.n/a')}</p>
              <p className="mb-0">
                <strong>{t('candidateReport.status')}:</strong>{' '}
                {report.evaluation_status ? (
                  <Badge bg={report.evaluation_status === 'completed' ? 'success' : report.evaluation_status === 'failed' ? 'danger' : 'warning'}>
                    {report.evaluation_status}
                  </Badge>
                ) : (
                  t('common.n/a')
                )}
              </p>
            </div>
          )}
        </Card.Body>
      </Card>
      
      <Row>
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">{t('candidateReport.environmentQuality')}</h6>
            </Card.Header>
            <Card.Body>
              <Table bordered>
                <tbody>
                  <tr>
                    <td>{t('candidateReport.voiceQuality')}</td>
                    <td>{qualityBadge(report.voice_quality)}</td>
                  </tr>
                  <tr>
                    <td>{t('candidateReport.backgroundQuality')}</td>
                    <td>{qualityBadge(report.background_quality)}</td>
                  </tr>
                  <tr>
                    <td>{t('candidateReport.faceVisibility')}</td>
                    <td>{qualityBadge(report.face_visibility)}</td>
                  </tr>
                  <tr>
                    <td>{t('candidateReport.lighting')}</td>
                    <td>{qualityBadge(report.lighting)}</td>
                  </tr>
                </tbody>
              </Table>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">{t('candidateReport.emotionConfidence')}</h6>
            </Card.Header>
            <Card.Body className="text-center">
              {report.dominant_emotion || (report.confidence_score ?? null) !== null ? (
                <>
                  <Row>
                    <Col>
                      <h5>{t('candidateReport.dominantEmotion')}</h5>
                      <span className={`emotion-badge ${getEmotionClass(report.dominant_emotion)}`}>
                        {report.dominant_emotion}
                      </span>
                      {emotionSampleCount > 0 && (
                        <p className="text-muted small mt-2 mb-0">{t('candidateReport.basedOnAnswers', { count: emotionSampleCount })}</p>
                      )}
                    </Col>
                    <Col>
                      <h5>{t('candidateReport.confidenceScore')}</h5>
                      <div className={`score-circle ${getScoreClass(report.confidence_score ?? 0)}`} style={{ width: '80px', height: '80px', fontSize: '18px' }}>
                        {formatPercent(report.confidence_score)}
                      </div>
                    </Col>
                  </Row>
                  {distribution.length > 1 && (
                    <div className="mt-3">
                      <small className="text-muted fw-semibold text-uppercase" style={{ fontSize: '0.7rem', letterSpacing: '0.05em' }}>
                        {t('candidateReport.emotionDistribution')}
                      </small>
                      <div className="d-flex flex-wrap justify-content-center gap-1 mt-2">
                        {distribution.map((d) => (
                          <span key={d.emotion} className={`emotion-badge ${getEmotionClass(d.emotion)}`}>
                            {d.emotion} ×{d.count}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-muted mb-0">{t('candidateReport.noEmotionData')}</p>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      {isEmployerView && (
        <Card className="border-0">
          <Card.Header className="bg-transparent px-0 pt-0 border-bottom-0">
            <h5 className="mb-0 fw-semibold">{t('candidateReport.questionBreakdown')}</h5>
          </Card.Header>
          <Card.Body className="px-0 pb-0">
            {report.answers.map((answer: any, idx: number) => (
              <InterviewFeedbackCard
                key={idx}
                questionNumber={idx + 1}
                questionText={answer.question || t('interviewDetail.questionN', { n: idx + 1 })}
                expectedAnswer={answer.expected_answer}
                answerText={answer.answer_text}
                score={answer.score ?? 0}
                emotion={answer.emotion}
                feedbackEn={answer.feedback_en || answer.feedback}
                feedbackAr={answer.feedback_ar}
                evidence={answer.evidence}
                videoUrl={answer.video_file_path ? answer.video_file_path.replace(/^uploads\//, '/static/') : undefined}
              />
            ))}
          </Card.Body>
        </Card>
      )}

      {isEmployerView && (
        <Card className="mt-4 border-0">
          <Card.Header className="bg-transparent px-0 pt-0 border-bottom-0">
            <div className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0 fw-semibold">{t('candidateReport.auditTrail')}</h5>
              {canManageEvaluations && (
                <Button variant="outline-primary" size="sm" onClick={handleReevaluate} disabled={reevaluating}>
                  {reevaluating ? t('candidateReport.reevaluating') : t('candidateReport.reevaluate')}
                </Button>
              )}
            </div>
          </Card.Header>
          <Card.Body className="px-0">
            {evaluationAudit.length === 0 ? (
              <p className="text-muted mb-0">{t('candidateReport.noRuns')}</p>
            ) : (
              <Accordion defaultActiveKey="0">
                {evaluationAudit.map((run: any, runIndex: number) => (
                  <Accordion.Item eventKey={`${runIndex}`} key={run.id}>
                    <Accordion.Header>
                      <span className="me-2">{t('candidateReport.runN', { id: run.id })}</span>
                      {runIndex === 0 && <Badge bg="primary" className="me-2">{t('candidateReport.latest')}</Badge>}
                      <Badge bg={run.status === 'completed' ? 'success' : run.status === 'failed' ? 'danger' : 'warning'}>
                        {run.status}
                      </Badge>
                    </Accordion.Header>
                    <Accordion.Body>
                      <Row className="mb-4 g-3">
                        <Col md={6}>
                          <p className="mb-1"><strong>{t('candidateReport.provider')}:</strong> {run.provider}</p>
                          <p className="mb-1"><strong>{t('candidateReport.model')}:</strong> {run.model_name || t('common.n/a')}</p>
                          <p className="mb-1"><strong>{t('candidateReport.configHash')}:</strong> {run.config_hash || t('common.n/a')}</p>
                        </Col>
                        <Col md={6}>
                          <p className="mb-1"><strong>{t('candidateReport.started')}:</strong> {formatDateTime(run.started_at)}</p>
                          <p className="mb-1"><strong>{t('common.completed')}:</strong> {formatDateTime(run.completed_at)}</p>
                          <p className="mb-1"><strong>{t('candidateReport.scoreDelta')}:</strong> {formatScoreDelta(run, evaluationAudit[runIndex + 1])}</p>
                          {run.raw_summary && (
                            <p className="mb-1"><strong>{t('candidateReport.summary')}:</strong> {run.raw_summary.total_score?.toFixed?.(1) || run.raw_summary.total_score || 0}% / {t('candidateReport.answers', { count: run.raw_summary.answer_count || 0 })}</p>
                          )}
                        </Col>
                      </Row>
                      {run.error && <p className="text-danger"><strong>{t('candidateReport.error')}:</strong> {run.error}</p>}
                      {run.scores.map((score: any, sIdx: number) => (
                        <InterviewFeedbackCard
                          key={score.id}
                          questionNumber={sIdx + 1}
                          questionText={score.question || t('interviewDetail.questionN', { n: score.question_id })}
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
      )}
    </div>
  )
}

export default CandidateReport
