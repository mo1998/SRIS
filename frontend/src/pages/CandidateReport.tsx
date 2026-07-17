import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Badge, Button, Table } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { FiArrowLeft, FiDownload } from 'react-icons/fi'

const CandidateReport: React.FC = () => {
  const { responseId } = useParams<{ responseId: string }>()
  const navigate = useNavigate()
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadReport()
  }, [responseId])
  
  const loadReport = async () => {
    try {
      const response = await api.reports.getCandidateReport(parseInt(responseId!))
      setReport(response.data)
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
      
      <Card>
        <Card.Header>
          <h5 className="mb-0">Question-by-Question Breakdown</h5>
        </Card.Header>
        <Card.Body>
          <Table striped bordered responsive>
            <thead>
              <tr>
                <th>#</th>
                <th>Question</th>
                <th>Score</th>
                <th>Emotion</th>
                <th>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {report.answers.map((answer: any, idx: number) => (
                <tr key={idx}>
                  <td>{idx + 1}</td>
                  <td style={{ maxWidth: '300px' }}>{answer.question}</td>
                  <td>
                    <Badge bg={answer.score >= 80 ? 'success' : answer.score >= 60 ? 'warning' : 'danger'}>
                      {answer.score?.toFixed(1) || 0}%
                    </Badge>
                  </td>
                  <td>
                    {answer.emotion && (
                      <span className={`emotion-badge ${getEmotionClass(answer.emotion)}`}>
                        {answer.emotion}
                      </span>
                    )}
                  </td>
                  <td style={{ maxWidth: '300px' }}>{answer.feedback}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card.Body>
      </Card>
    </div>
  )
}

export default CandidateReport
