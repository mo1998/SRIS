import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Button, Table, Badge } from 'react-bootstrap'
import { api } from '../services/api'
import { Link } from 'react-router-dom'
import { FiPlus, FiUsers, FiCheckCircle, FiXCircle, FiEye } from 'react-icons/fi'

const EmployerDashboard: React.FC = () => {
  const [interviews, setInterviews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  
  useEffect(() => {
    loadInterviews()
  }, [])
  
  const loadInterviews = async () => {
    try {
      const response = await api.interviews.list()
      setInterviews(response.data)
    } catch (error) {
      console.error('Failed to load interviews:', error)
    } finally {
      setLoading(false)
    }
  }
  
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'draft':
        return <Badge bg="secondary">Draft</Badge>
      case 'active':
        return <Badge bg="success">Active</Badge>
      case 'completed':
        return <Badge bg="primary">Completed</Badge>
      case 'cancelled':
        return <Badge bg="danger">Cancelled</Badge>
      default:
        return <Badge bg="secondary">{status}</Badge>
    }
  }
  
  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Employer Dashboard</h1>
        <Link to="/employer/interviews/create">
          <Button variant="primary">
            <FiPlus className="me-2" />
            Create Interview
          </Button>
        </Link>
      </div>
      
      <Row className="mb-4">
        <Col md={4}>
          <Card>
            <Card.Body>
              <Card.Title>
                <FiUsers className="me-2" />
                Total Interviews
              </Card.Title>
              <Card.Text className="display-4">{interviews.length}</Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card>
            <Card.Body>
              <Card.Title>
                <FiCheckCircle className="me-2" />
                Active Interviews
              </Card.Title>
              <Card.Text className="display-4">
                {interviews.filter(i => i.status === 'active').length}
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card>
            <Card.Body>
              <Card.Title>
                <FiXCircle className="me-2" />
                Completed Interviews
              </Card.Title>
              <Card.Text className="display-4">
                {interviews.filter(i => i.status === 'completed').length}
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      
      <Card>
        <Card.Header>
          <h5 className="mb-0">Your Interviews</h5>
        </Card.Header>
        <Card.Body>
          {loading ? (
            <p>Loading...</p>
          ) : interviews.length === 0 ? (
            <p className="text-center">No interviews created yet. Create your first interview!</p>
          ) : (
            <Table striped bordered hover responsive>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Duration</th>
                  <th>Pass Score</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {interviews.map((interview) => (
                  <tr key={interview.id}>
                    <td>{interview.title}</td>
                    <td>{getStatusBadge(interview.status)}</td>
                    <td>{interview.duration_minutes} min</td>
                    <td>{interview.pass_score}%</td>
                    <td>{new Date(interview.created_at).toLocaleDateString()}</td>
                    <td>
                      <Link to={`/employer/interviews/${interview.id}`}>
                        <Button variant="outline-primary" size="sm">
                          <FiEye className="me-1" />
                          View
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card.Body>
      </Card>
    </div>
  )
}

export default EmployerDashboard
