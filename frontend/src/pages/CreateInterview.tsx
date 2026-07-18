import React, { useEffect, useState } from 'react'
import { Form, Button, Card, Alert, Row, Col, Badge } from 'react-bootstrap'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { FiPlus, FiTrash2, FiSave, FiLayers } from 'react-icons/fi'

const CreateInterview: React.FC = () => {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<any[]>([])
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    duration_minutes: 30,
    max_attempts: 1,
    pass_score: 70.0
  })
  const [questions, setQuestions] = useState<any[]>([
    { question_text: '', expected_answer: '', question_type: 'text', weight: 1.0, order_index: 0, rubric_criteria: [] }
  ])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [templateLoading, setTemplateLoading] = useState(false)

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      const response = await api.interviews.listTemplates()
      setTemplates(response.data)
    } catch (err) {
      console.error('Failed to load templates:', err)
    }
  }

  const handleTemplateSelect = async (templateId: string) => {
    setSelectedTemplateId(templateId)
    setSelectedTemplate(null)

    if (!templateId) {
      return
    }

    setTemplateLoading(true)
    try {
      const response = await api.interviews.getTemplate(parseInt(templateId))
      const template = response.data
      setSelectedTemplate(template)
      setFormData((current) => ({
        ...current,
        title: current.title || template.name,
        description: current.description || template.description || '',
        duration_minutes: template.duration_minutes,
        pass_score: template.pass_score,
      }))
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load template')
    } finally {
      setTemplateLoading(false)
    }
  }
  
  const addQuestion = () => {
    setQuestions([...questions, { 
      question_text: '', 
      expected_answer: '', 
      question_type: 'text', 
      weight: 1.0,
      order_index: questions.length,
      rubric_criteria: []
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

  const addRubricCriterion = (questionIndex: number) => {
    const updated = [...questions]
    const currentCriteria = updated[questionIndex].rubric_criteria || []
    updated[questionIndex] = {
      ...updated[questionIndex],
      rubric_criteria: [
        ...currentCriteria,
        { name: '', description: '', weight: 1.0, order_index: currentCriteria.length }
      ]
    }
    setQuestions(updated)
  }

  const updateRubricCriterion = (questionIndex: number, criterionIndex: number, field: string, value: any) => {
    const updated = [...questions]
    const currentCriteria = [...(updated[questionIndex].rubric_criteria || [])]
    currentCriteria[criterionIndex] = { ...currentCriteria[criterionIndex], [field]: value }
    updated[questionIndex] = { ...updated[questionIndex], rubric_criteria: currentCriteria }
    setQuestions(updated)
  }

  const removeRubricCriterion = (questionIndex: number, criterionIndex: number) => {
    const updated = [...questions]
    updated[questionIndex] = {
      ...updated[questionIndex],
      rubric_criteria: (updated[questionIndex].rubric_criteria || []).filter((_: any, index: number) => index !== criterionIndex)
    }
    setQuestions(updated)
  }
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    
    try {
      const interviewData = {
        ...formData,
        questions: questions.map((q, idx) => ({
          ...q,
          order_index: idx,
          rubric_criteria: (q.rubric_criteria || [])
            .filter((criterion: any) => criterion.name.trim())
            .map((criterion: any, criterionIndex: number) => ({
              ...criterion,
              order_index: criterionIndex,
            }))
        }))
      }
      
      const response = await api.interviews.create(interviewData)
      navigate(`/employer/interviews/${response.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create interview')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateFromTemplate = async () => {
    if (!selectedTemplate) {
      setError('Select a template first')
      return
    }

    setError('')
    setLoading(true)

    try {
      const response = await api.interviews.createFromTemplate(selectedTemplate.id, {
        title: formData.title,
        description: formData.description,
        duration_minutes: formData.duration_minutes,
        max_attempts: formData.max_attempts,
        pass_score: formData.pass_score,
      })
      navigate(`/employer/interviews/${response.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create interview from template')
    } finally {
      setLoading(false)
    }
  }
  
  return (
    <div>
      <h1 className="mb-4">Create New Interview</h1>
      
      {error && <Alert variant="danger">{error}</Alert>}

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">
            <FiLayers className="me-2" />
            Start From Template
          </h5>
        </Card.Header>
        <Card.Body>
          <Row className="align-items-end">
            <Col md={8}>
              <Form.Group className="mb-3" controlId="interview-template">
                <Form.Label>Template</Form.Label>
                <Form.Select
                  value={selectedTemplateId}
                  onChange={(event) => handleTemplateSelect(event.target.value)}
                >
                  <option value="">Choose a template...</option>
                  {templates.map((template) => (
                    <option key={template.id} value={template.id}>
                      {template.name}
                    </option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Button
                type="button"
                variant="outline-primary"
                className="w-100 mb-3"
                disabled={!selectedTemplate || loading}
                onClick={handleCreateFromTemplate}
              >
                <FiLayers className="me-2" />
                Create from Template
              </Button>
            </Col>
          </Row>

          {templateLoading && <p className="mb-0">Loading template...</p>}

          {selectedTemplate && (
            <div>
              <div className="d-flex gap-2 align-items-center mb-2">
                <h6 className="mb-0">{selectedTemplate.name}</h6>
                <Badge bg="secondary">{selectedTemplate.role_category}</Badge>
                <Badge bg="light" text="dark">{selectedTemplate.duration_minutes} min</Badge>
              </div>
              <p className="text-muted">{selectedTemplate.description}</p>
              <ol className="mb-0">
                {selectedTemplate.questions.map((question: any) => (
                  <li key={question.id} className="mb-2">
                    <strong>{question.question_text}</strong>
                    <br />
                    <small className="text-muted">Weight: {question.weight}x</small>
                    {(question.rubric_criteria || []).length > 0 && (
                      <ul className="mt-1">
                        {question.rubric_criteria.map((criterion: any) => (
                          <li key={criterion.id}>
                            <small>
                              <strong>{criterion.name}</strong>
                              {criterion.description ? `: ${criterion.description}` : ''}
                            </small>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </Card.Body>
      </Card>
      
      <Form onSubmit={handleSubmit}>
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0">Interview Details</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3" controlId="interview-title">
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
              <Form.Group className="mb-3" controlId={`question-text-${index}`}>
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

              <div className="border-top pt-3 mt-2">
                <div className="d-flex justify-content-between align-items-center mb-3">
                  <h6 className="mb-0">Rubric Criteria</h6>
                  <Button
                    type="button"
                    variant="outline-secondary"
                    size="sm"
                    onClick={() => addRubricCriterion(index)}
                  >
                    <FiPlus className="me-1" />
                    Add Criterion
                  </Button>
                </div>

                {(question.rubric_criteria || []).length === 0 ? (
                  <p className="text-muted mb-0">No rubric criteria added yet.</p>
                ) : (
                  question.rubric_criteria.map((criterion: any, criterionIndex: number) => (
                    <Card key={criterionIndex} className="mb-3 bg-light">
                      <Card.Body>
                        <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
                          <strong>Criterion {criterionIndex + 1}</strong>
                          <Button
                            type="button"
                            variant="outline-danger"
                            size="sm"
                            onClick={() => removeRubricCriterion(index, criterionIndex)}
                          >
                            <FiTrash2 />
                          </Button>
                        </div>
                        <Row>
                          <Col md={8}>
                            <Form.Group className="mb-3" controlId={`rubric-name-${index}-${criterionIndex}`}>
                              <Form.Label>Name</Form.Label>
                              <Form.Control
                                value={criterion.name}
                                onChange={(event) => updateRubricCriterion(index, criterionIndex, 'name', event.target.value)}
                                placeholder="Clarity, completeness, examples..."
                              />
                            </Form.Group>
                          </Col>
                          <Col md={4}>
                            <Form.Group className="mb-3" controlId={`rubric-weight-${index}-${criterionIndex}`}>
                              <Form.Label>Weight</Form.Label>
                              <Form.Control
                                type="number"
                                value={criterion.weight}
                                onChange={(event) => updateRubricCriterion(index, criterionIndex, 'weight', parseFloat(event.target.value))}
                                min={0.5}
                                max={5}
                                step={0.5}
                              />
                            </Form.Group>
                          </Col>
                        </Row>
                        <Form.Group controlId={`rubric-description-${index}-${criterionIndex}`}>
                          <Form.Label>Description</Form.Label>
                          <Form.Control
                            as="textarea"
                            rows={2}
                            value={criterion.description}
                            onChange={(event) => updateRubricCriterion(index, criterionIndex, 'description', event.target.value)}
                            placeholder="What should a strong answer demonstrate?"
                          />
                        </Form.Group>
                      </Card.Body>
                    </Card>
                  ))
                )}
              </div>
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
