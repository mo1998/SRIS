import React, { useEffect, useState } from 'react'
import { Table, Badge, Button } from 'react-bootstrap'
import { api } from '../services/api'
import { FiEye } from 'react-icons/fi'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

const MyResults: React.FC = () => {
  const [results, setResults] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  
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
  
  if (loading) return <LoadingSpinner text="Loading your results..." />
  
  return (
    <div>
      <PageHeader title="My Results" subtitle="View your interview performance and feedback" />
      
      {results.length === 0 ? (
        <EmptyState
          title="No results yet"
          description="You haven't completed any interviews yet."
        />
      ) : (
        <div className="table-responsive">
          <Table striped bordered hover>
            <thead>
              <tr>
                <th>Interview</th>
                <th>Score</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Voice Quality</th>
                <th>Completed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result, idx) => (
                <tr key={idx}>
                  <td className="fw-medium">{result.interview_title}</td>
                  <td>
                    <span className={`badge rounded-pill fs-6 px-3 py-2 ${result.total_score >= 80 ? 'bg-success' : result.total_score >= 60 ? 'bg-warning text-dark' : 'bg-danger'}`}>
                      {result.total_score.toFixed(1)}%
                    </span>
                  </td>
                  <td>
                    <Badge bg={result.passed ? 'success' : 'danger'}>
                      {result.passed ? 'PASSED' : 'FAILED'}
                    </Badge>
                  </td>
                  <td>{result.confidence_score?.toFixed(1)}%</td>
                  <td>{result.voice_quality?.toFixed(1)}%</td>
                  <td className="text-muted small">
                    {result.completed_at ? new Date(result.completed_at).toLocaleDateString() : 'N/A'}
                  </td>
                  <td>
                    <Button variant="outline-primary" size="sm" onClick={() => navigate(`/employee/candidate/${result.response_id}`)}>
                      <FiEye className="me-1" /> View
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </div>
      )}
    </div>
  )
}

export default MyResults
