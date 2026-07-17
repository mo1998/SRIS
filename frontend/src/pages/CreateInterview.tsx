import React, { useState } from 'react'
import { Form, Button, Card, Alert, Row, Col } from 'react-bootstrap'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { FiPlus, FiTrash2, FiSave } from 'react-icons/fi'

const CreateInterview: React.FC = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    duration_minutes: 30,
    max_attempts: 1,
    pass_score: 70.0
  })
  const [questions, setQuestions] = useState<any[]>([
    { question_text: '', expected_answer: '', question_type: 'text', weight: 1.0, order_index: 0 }
  ])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  
  const addQuestion = () => {
    setQuestions([...questions, { 
      question_text: '', 
      expected_answer: '', 
      question_type: 'text', 
      weight: 1.0,
      order_index: questions.length 
    }])
  }
  
  const removeQuestion = (index: number) => {
    if (questions.length > 1) {
      setQuestions(questions.filter((_, i) => i !== index))
    }
  }
  
  const updateQuestion = (index: number, field: string, value: any) => {
    const updated = [...questions]
    updated[index] = { ...updated[index], [field]: value }
    setQuestions(updated)
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      const interviewData = {
        ...formData,
        questions: questions.map((q, idx) => ({ ...q, order_index: idx }))
      }
      
      const response = await api.interviews.create(interviewData)
      navigate(`/employer/interviews/${response.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create interview')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div>
      <h1 className="mb-4">Create New Interview</h1>
      
      {error && <Alert variant="danger">{error}</Alert>}
      
      <Form onSubmit={handleSubmit}>
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0">Interview Details</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Interview Title *</Form.Label>
                  <Form.Control
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({...formData, title: e.target.value})}
                    required
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Duration (minutes)</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.duration_minutes}
                    onChange={(e) => setFormData({...formData, duration_minutes: parseInt(e.target.value)})}
                    min={5}
                    max={120}
                  />
                </Form.Group>
              </Col>
            </Row>
            
            <Form.Group className="mb-3">
              <Form.Label>Description</Form.Label>
              <Form.Control
                as="textarea"
                rows={3}
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
              />
            </Form.Group>
            
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Maximum Attempts</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.max_attempts}
                    onChange={(e) => setFormData({...formData, max_attempts: parseInt(e.target.value)})}
                    min={1}
                    max={10}
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label>Pass Score (%)</Form.Label>
                  <Form.Control
                    type="number"
                    value={formData.pass_score}
                    onChange={(e) => setFormData({...formData, pass_score: parseFloat(e.target.value)})}
                    min={0}
                    max={100}
                  />
                </Form.Group>
              </Col>
            </Row>
          </Card.Body>
        </Card>
        
        <h4 className="mb-3">Questions</h4>
        
        {questions.map((question, index) => (
          <Card key={index} className="mb-3">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h6 className="mb-0">Question {index + 1}</h6>
              <Button
                variant="outline-danger"
                size="sm"
                onClick={() => removeQuestion(index)}
                disabled={questions.length === 1}
              >
                <FiTrash2 />
              </Button>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>Question Text *</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={2}
                  value={question.question_text}
                  onChange={(e) => updateQuestion(index, 'question_text', e.target.value)}
                  required
                />
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>Expected Answer (for AI evaluation)</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={question.expected_answer}
                  onChange={(e) => updateQuestion(index, 'expected_answer', e.target.value)}
                  placeholder="Provide a reference answer to help AI evaluate responses"
                />
              </Form.Group>
              
              <Row>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>Question Type</Form.Label>
                    <Form.Select
                      value={question.question_type}
                      onChange={(e) => updateQuestion(index, 'question_type', e.target.value)}
                    >
                      <option value="text">Text/Voice Answer</option>
                      <option value="multiple_choice">Multiple Choice</option>
                      <option value="coding">Coding</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>Weight (importance)</Form.Label>
                    <Form.Control
                      type="number"
                      value={question.weight}
                      onChange={(e) => updateQuestion(index, 'weight', parseFloat(e.target.value))}
                      min={0.5}
                      max={5}
                      step={0.5}
                    />
                  </Form.Group>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        ))}
        
        <Button variant="outline-primary" onClick={addQuestion} className="mb-4">
          <FiPlus className="me-2" />
          Add Question
        </Button>
        
        <div className="d-flex gap-2">
          <Button variant="primary" type="submit" disabled={loading}>
            <FiSave className="me-2" />
            {loading ? 'Creating...' : 'Create Interview'}
          </Button>
          <Button variant="secondary" onClick={() => navigate(-1)}>
            Cancel
          </Button>
        </div>
      </Form>
    </div>
  )
}

export default CreateInterview
