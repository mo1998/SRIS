import React, { useEffect, useState } from 'react'
import { Card, Table, Badge, Button } from 'react-bootstrap'
import { api } from '../services/api'
import { FiEye } from 'react-icons/fi'
import { Link } from 'react-router-dom'

const MyResults: React.FC = () => {
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadResults()
  }, [])
  
  const loadResults = async () => {
    try {
      const response = await api.reports.getMyResults()
      setResults(response.data)
    } catch (error) {
      console.error('Failed to load results:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const getScoreClass = (score: number) => {
    if (score >= 80) return 'score-high'
    if (score >= 60) return 'score-medium'
    return 'score-low'
  }
  
  return (
    <div>
      <h1 className="mb-4">My Interview Results</h1>
      
      {loading ? (
        <p>Loading your results...</p>
      ) : results.length === 0 ? (
        <Card>
          <Card.Body className="text-center">
            <p className="text-muted">You haven't completed any interviews yet.</p>
          </Card.Body>
        </Card>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>Interview</th>
              <th>Score</th>
              <th>Status</th>
              <th>Confidence</th>
              <th>Voice Quality</th>
              <th>Face Visibility</th>
              <th>Dominant Emotion</th>
              <th>Completed</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {results.map((result, idx) => (
              <tr key={idx}>
                <td><strong>{result.interview_title}</strong></td>
                <td>
                  <div className={`score-circle ${getScoreClass(result.total_score)}`} style={{ width: '60px', height: '60px', fontSize: '14px', margin: '0 auto' }}>
                    {result.total_score.toFixed(1)}%
                  </div>
                </td>
                <td>
                  <Badge bg={result.passed ? 'success' : 'danger'}>
                    {result.passed ? 'PASSED' : 'FAILED'}
                  </Badge>
                </td>
                <td>{result.confidence_score?.toFixed(1)}%</td>
                <td>{result.voice_quality?.toFixed(1)}%</td>
                <td>{result.face_visibility?.toFixed(1)}%</td>
                <td>
                  <span className={`emotion-badge emotion-${result.dominant_emotion?.toLowerCase()}`}>
                    {result.dominant_emotion}
                  </span>
                </td>
                <td>{result.completed_at ? new Date(result.completed_at).toLocaleDateString() : 'N/A'}</td>
                <td>
                  <Link to={`/employee/candidate/${result.response_id}`}>
                    <Button variant="outline-primary" size="sm">
                      <FiEye className="me-1" />
                      View Details
                    </Button>
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  )
}

export default MyResults
