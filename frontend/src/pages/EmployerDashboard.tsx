import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Table, Badge } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { FiPlus, FiUsers, FiCheckCircle, FiXCircle, FiEye, FiBarChart2 } from 'react-icons/fi'
import StatCard from '../components/ui/StatCard'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'
import ConfirmModal from '../components/ui/ConfirmModal'
import { useToast } from '../hooks/useToast'
import { useRealTimeRefresh } from '../hooks/useRealTimeRefresh'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend, ArcElement)

const STATUS_BG: Record<string, string> = {
  draft: 'secondary',
  active: 'success',
  completed: 'primary',
  cancelled: 'danger',
}

const EmployerDashboard: React.FC = () => {
  const [interviews, setInterviews] = useState<any[]>([])
  const [members, setMembers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const navigate = useNavigate()
  const toast = useToast()
  const { t, i18n } = useTranslation()

  const statusLabelMap: Record<string, string> = {
    draft: t('dashboard.draft'),
    active: t('dashboard.active'),
    completed: t('dashboard.completed'),
    cancelled: t('dashboard.cancelled'),
  }

  const getStatusBadge = (status: string) => (
    <Badge bg={STATUS_BG[status] || 'secondary'}>{statusLabelMap[status] || status.charAt(0).toUpperCase() + status.slice(1)}</Badge>
  )

  useEffect(() => {
    loadInterviews()
  }, [])

  const loadInterviews = async () => {
    try {
      const [interviewsResponse, membersResponse] = await Promise.all([
        api.interviews.list(),
        api.users.getOrganizationMembers(),
      ])
      setInterviews(interviewsResponse.data)
      setMembers(membersResponse.data)
    } catch (error) {
      toast.error(t('dashboard.loadFailed'), t('dashboard.loadError'))
    } finally {
      setLoading(false)
    }
   }

   // Keep the dashboard in sync when interviews/responses/evaluations/decisions
   // change anywhere in the system, without a manual refresh.
   useRealTimeRefresh(loadInterviews, [])

   const handleDelete = async () => {
    if (deletingId === null) return
    try {
      await api.interviews.delete(deletingId)
      setInterviews(prev => prev.filter(i => i.id !== deletingId))
      toast.success(t('dashboard.deleted'))
    } catch {
      toast.error(t('dashboard.deleteFailed'))
    } finally {
      setShowDeleteModal(false)
      setDeletingId(null)
    }
  }

  const activeCount = interviews.filter(i => i.status === 'active').length
  const completedCount = interviews.filter(i => i.status === 'completed').length
  const draftCount = interviews.filter(i => i.status === 'draft').length

  const statusChartData = {
    labels: [t('dashboard.active'), t('dashboard.completed'), t('dashboard.draft'), t('dashboard.cancelled')],
    datasets: [{
      data: [activeCount, completedCount, draftCount, interviews.length - activeCount - completedCount - draftCount],
      backgroundColor: ['#10b981', '#4f46e5', '#f59e0b', '#ef4444'],
      borderWidth: 0,
    }],
  }

  const monthFormatter = new Intl.DateTimeFormat(i18n.language === 'ar' ? 'ar' : 'en', { month: 'short' })

  const monthlyData = (() => {
    const months: { key: string; label: string; count: number }[] = []
    const now = new Date()
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      months.push({ key: `${d.getFullYear()}-${d.getMonth()}`, label: monthFormatter.format(d), count: 0 })
    }
    interviews.forEach((interview) => {
      if (!interview.created_at) return
      const created = new Date(interview.created_at)
      const month = months.find((m) => m.key === `${created.getFullYear()}-${created.getMonth()}`)
      if (month) month.count += 1
    })
    return {
      labels: months.map((m) => m.label),
      datasets: [{
        label: t('dashboard.interviews'),
        data: months.map((m) => m.count),
        backgroundColor: 'var(--color-primary)',
        borderRadius: 6,
      }],
    }
  })()

  if (loading) return <LoadingSpinner text={t('dashboard.loading')} />

  return (
    <div>
      <PageHeader
        title={t('dashboard.title')}
        subtitle={t('dashboard.subtitle')}
        actions={
          <Button variant="primary" onClick={() => navigate('/employer/interviews/create')}>
            <FiPlus className="me-2" />
            {t('dashboard.createInterview')}
          </Button>
        }
      />

      <Row className="mb-4 g-3">
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiBarChart2 />} label={t('dashboard.totalInterviews')} value={interviews.length} />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiCheckCircle />} label={t('dashboard.active')} value={activeCount} variant="success" />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiUsers />} label={t('dashboard.completed')} value={completedCount} variant="info" />
        </Col>
        <Col xs={12} sm={6} xxl={3}>
          <StatCard icon={<FiXCircle />} label={t('dashboard.teamMembers')} value={members.length} variant="warning" />
        </Col>
      </Row>

      <Row className="mb-4 g-3">
        <Col md={7}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">{t('dashboard.interviewTrends')}</h6>
            </Card.Header>
            <Card.Body>
              <Bar data={monthlyData} options={{ responsive: true, plugins: { legend: { display: false } } }} />
            </Card.Body>
          </Card>
        </Col>
        <Col md={5}>
          <Card className="h-100">
            <Card.Header>
              <h6 className="mb-0 fw-semibold">{t('dashboard.statusDistribution')}</h6>
            </Card.Header>
            <Card.Body className="d-flex align-items-center justify-content-center">
              {interviews.length === 0 ? (
                <p className="text-muted mb-0">{t('dashboard.noInterviewsYet')}</p>
              ) : (
                <div style={{ maxWidth: 220 }}>
                  <Doughnut data={statusChartData} options={{ cutout: '70%', plugins: { legend: { position: 'bottom' } } }} />
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>

      <Card>
        <Card.Header>
          <h6 className="mb-0 fw-semibold">{t('dashboard.yourInterviews')}</h6>
        </Card.Header>
        <Card.Body>
          {interviews.length === 0 ? (
            <EmptyState
              title={t('dashboard.noInterviewsYet')}
              description={t('dashboard.createFirst')}
              actionLabel={t('dashboard.createInterview')}
              onAction={() => navigate('/employer/interviews/create')}
            />
          ) : (
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>{t('common.title')}</th>
                  <th>{t('common.status')}</th>
                  <th>{t('dashboard.duration')}</th>
                  <th>{t('dashboard.passScore')}</th>
                  <th>{t('dashboard.created')}</th>
                  <th>{t('common.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {interviews.map((interview) => (
                  <tr key={interview.id}>
                    <td className="fw-medium">{interview.title}</td>
                    <td>{getStatusBadge(interview.status)}</td>
                    <td>{t('dashboard.minutesShort', { count: interview.duration_minutes })}</td>
                    <td>{interview.pass_score}%</td>
                    <td className="text-muted small">{new Date(interview.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="d-flex gap-2">
                        <Button variant="outline-primary" size="sm" onClick={() => navigate(`/employer/interviews/${interview.id}`)}>
                          <FiEye /> {t('common.view')}
                        </Button>
                        {interview.status === 'draft' && (
                          <Button variant="outline-danger" size="sm" onClick={() => { setDeletingId(interview.id); setShowDeleteModal(true) }}>
                            {t('dashboard.delete')}
                          </Button>
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

      <ConfirmModal
        show={showDeleteModal}
        title={t('dashboard.deleteTitle')}
        message={t('dashboard.deleteConfirm')}
        confirmLabel={t('dashboard.delete')}
        onConfirm={handleDelete}
        onCancel={() => { setShowDeleteModal(false); setDeletingId(null) }}
      />
    </div>
  )
}

export default EmployerDashboard
