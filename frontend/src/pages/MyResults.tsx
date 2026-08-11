import React, { useEffect, useState } from 'react'
import { Table, Badge, Button } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { FiEye } from 'react-icons/fi'
import { useNavigate, Link } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

const MyResults: React.FC = () => {
  const { t } = useTranslation()
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
  
  if (loading) return <LoadingSpinner text={t('resultsPortal.loading')} />
  
  return (
    <div>
      <PageHeader title={t('myResults.title')} subtitle={t('myResults.subtitle')} />
      
      {results.length === 0 ? (
        <EmptyState
          title={t('myResults.noResults')}
          description={t('myResults.noResultsDesc')}
        />
      ) : (
        <div className="table-responsive">
          <Table striped bordered hover>
            <thead>
              <tr>
                <th>{t('myResults.interview')}</th>
                <th>{t('myResults.score')}</th>
                <th>{t('myResults.status')}</th>
                <th>{t('myResults.confidence')}</th>
                <th>{t('myResults.voiceQuality')}</th>
                <th>{t('myResults.completed')}</th>
                <th>{t('common.actions')}</th>
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
                      {result.passed ? t('common.passed') : t('common.failed')}
                    </Badge>
                  </td>
                  <td>{result.confidence_score?.toFixed(1)}%</td>
                  <td>{result.voice_quality?.toFixed(1)}%</td>
                  <td className="text-muted small">
                    {result.completed_at ? new Date(result.completed_at).toLocaleDateString() : t('common.n/a')}
                  </td>
                    <td>
                      <Link to={`/employee/candidate/${result.response_id}`}>
                        <Button variant="outline-primary" size="sm">
                          <FiEye className="me-1" /> {t('common.view')}
                        </Button>
                      </Link>
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
