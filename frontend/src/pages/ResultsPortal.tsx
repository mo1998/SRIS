import React, { useEffect, useState } from 'react'
import { Container, Badge, Card, Alert, Row, Col } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const ResultsPortal: React.FC = () => {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.invitations
      .getResults(token)
      .then((response) => setReport(response.data))
      .catch((err) => setError(err.response?.data?.detail || t('resultsPortal.error')))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <LoadingSpinner text={t('resultsPortal.loading')} />

  return (
    <Container className="py-5" style={{ maxWidth: 860 }}>
      <Link to="/login" className="text-muted small d-inline-block mb-3">← {t('resultsPortal.back')}</Link>
      {error ? (
        <Alert variant="warning">{error}</Alert>
      ) : report ? (
        <Card className="shadow-sm">
          <Card.Body className="p-4 p-md-5">
            <h2 className="mb-1">{report.interview_title}</h2>
            <p className="text-muted mb-4">{t('resultsPortal.resultsFor', { name: report.candidate_name })}</p>

            <Row className="mb-4 g-3">
              <Col md={4}>
                <Card className="text-center h-100 bg-light">
                  <Card.Body>
                    <div className="text-muted small text-uppercase">{t('resultsPortal.overallScore')}</div>
                    <div className={`fs-1 fw-bold ${report.total_score >= 80 ? 'text-success' : report.total_score >= 60 ? 'text-warning' : 'text-danger'}`}>
                      {report.total_score.toFixed(1)}%
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="text-center h-100 bg-light">
                  <Card.Body>
                    <div className="text-muted small text-uppercase">{t('resultsPortal.result')}</div>
                    <div className="fs-2 fw-bold">
                      <Badge bg={report.passed ? 'success' : 'danger'}>
                        {report.passed ? t('common.passed') : t('resultsPortal.didNotPass')}
                      </Badge>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="text-center h-100 bg-light">
                  <Card.Body>
                    <div className="text-muted small text-uppercase">{t('resultsPortal.completed')}</div>
                    <div className="fs-5 fw-semibold">
                      {report.completed_at ? new Date(report.completed_at).toLocaleDateString() : t('common.n/a')}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            <h5 className="mb-3">{t('resultsPortal.perQuestionFeedback')}</h5>
            {report.answers.map((answer: any, idx: number) => (
              <Card key={idx} className="mb-3">
                <Card.Body>
                  <div className="d-flex justify-content-between align-items-start mb-2">
                    <div className="fw-medium">{answer.question}</div>
                    <span className={`badge rounded-pill ${answer.score >= 80 ? 'bg-success' : answer.score >= 60 ? 'bg-warning text-dark' : 'bg-danger'}`}>
                      {answer.score.toFixed ? answer.score.toFixed(1) : answer.score}%
                    </span>
                  </div>
                  {answer.transcript && (
                    <p className="text-muted mb-1 small">
                      <strong>{t('resultsPortal.yourSpokenAnswer')}</strong> {answer.transcript}
                    </p>
                  )}
                  {answer.answer_text && (
                    <p className="text-muted mb-1 small">
                      <strong>{t('resultsPortal.yourAnswer')}</strong> {answer.answer_text}
                    </p>
                  )}
                  {answer.feedback && <p className="mb-0">{answer.feedback}</p>}
                </Card.Body>
              </Card>
            ))}

            {report.ai_disclosure && (
              <Alert variant="info" className="mt-4 small">{report.ai_disclosure}</Alert>
            )}
          </Card.Body>
        </Card>
      ) : (
        <Alert variant="secondary">{t('resultsPortal.noResults')}</Alert>
      )}
    </Container>
  )
}

export default ResultsPortal
