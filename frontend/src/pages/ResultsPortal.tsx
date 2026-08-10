import React, { useEffect, useState } from 'react'
import { Container, Badge, Card, Alert, Row, Col } from 'react-bootstrap'
import { useParams, Link } from 'react-router-dom'
import { api } from '../services/api'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const ResultsPortal: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    api.invitations
      .getResults(token)
      .then((response) => setReport(response.data))
      .catch((err) => setError(err.response?.data?.detail || 'Unable to load your results.'))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) return <LoadingSpinner text="Loading your results..." />

  return (
    <Container className="py-5" style={{ maxWidth: 860 }}>
      <Link to="/login" className="text-muted small d-inline-block mb-3">← Back</Link>
      {error ? (
        <Alert variant="warning">{error}</Alert>
      ) : report ? (
        <Card className="shadow-sm">
          <Card.Body className="p-4 p-md-5">
            <h2 className="mb-1">{report.interview_title}</h2>
            <p className="text-muted mb-4">Results for {report.candidate_name}</p>

            <Row className="mb-4 g-3">
              <Col md={4}>
                <Card className="text-center h-100 bg-light">
                  <Card.Body>
                    <div className="text-muted small text-uppercase">Overall Score</div>
                    <div className={`fs-1 fw-bold ${report.total_score >= 80 ? 'text-success' : report.total_score >= 60 ? 'text-warning' : 'text-danger'}`}>
                      {report.total_score.toFixed(1)}%
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="text-center h-100 bg-light">
                  <Card.Body>
                    <div className="text-muted small text-uppercase">Result</div>
                    <div className="fs-2 fw-bold">
                      <Badge bg={report.passed ? 'success' : 'danger'}>
                        {report.passed ? 'PASSED' : 'DID NOT PASS'}
                      </Badge>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="text-center h-100 bg-light">
                  <Card.Body>
                    <div className="text-muted small text-uppercase">Completed</div>
                    <div className="fs-5 fw-semibold">
                      {report.completed_at ? new Date(report.completed_at).toLocaleDateString() : 'N/A'}
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            </Row>

            <h5 className="mb-3">Per-Question Feedback</h5>
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
                      <strong>Your spoken answer:</strong> {answer.transcript}
                    </p>
                  )}
                  {answer.answer_text && (
                    <p className="text-muted mb-1 small">
                      <strong>Your answer:</strong> {answer.answer_text}
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
        <Alert variant="secondary">No results found.</Alert>
      )}
    </Container>
  )
}

export default ResultsPortal
