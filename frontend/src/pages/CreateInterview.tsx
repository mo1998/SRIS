import React, { useEffect, useState } from 'react'
import { Form, Button, Card, Alert, Row, Col, Badge } from 'react-bootstrap'
import { api } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { FiPlus, FiTrash2, FiSave, FiLayers, FiBookOpen } from 'react-icons/fi'
import PageHeader from '../components/ui/PageHeader'
import ErrorAlert from '../components/ui/ErrorAlert'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const CreateInterview: React.FC = () => {
  const navigate = useNavigate()
  const { t } = useTranslation()
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
  const [bankEntries, setBankEntries] = useState<any[]>([])
  const [bankLoading, setBankLoading] = useState(false)

  useEffect(() => {
    loadTemplates()
    loadQuestionBank()
  }, [])

  const loadQuestionBank = async () => {
    setBankLoading(true)
    try {
      const response = await api.interviews.listQuestionBank()
      setBankEntries(response.data)
    } catch (err) {
      console.error('Failed to load question bank:', err)
    } finally {
      setBankLoading(false)
    }
  }

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
      setError(err.response?.data?.detail || t('createInterview.loadTemplateFailed'))
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
      setError(err.response?.data?.detail || t('createInterview.createFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleCreateFromTemplate = async () => {
    if (!selectedTemplate) {
      setError(t('createInterview.selectTemplateFirst'))
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
      setError(err.response?.data?.detail || t('createInterview.templateFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleLoadTemplateQuestions = () => {
    if (!selectedTemplate || !selectedTemplate.questions?.length) {
      setError(t('createInterview.templateNoQuestions'))
      return
    }
    const loaded = selectedTemplate.questions.map((question: any, idx: number) => ({
      question_text: question.question_text,
      expected_answer: question.expected_answer || '',
      question_type: question.question_type || 'text',
      weight: question.weight || 1.0,
      order_index: idx,
      rubric_criteria: (question.rubric_criteria || []).map((criterion: any, cIdx: number) => ({
        name: criterion.name,
        description: criterion.description || '',
        weight: criterion.weight || 1.0,
        order_index: cIdx,
      })),
    }))
    setQuestions(loaded)
    setError('')
  }

  const handleAddFromBank = (entry: any) => {
    setQuestions([...questions, {
      question_text: entry.question_text,
      expected_answer: entry.expected_answer || '',
      question_type: entry.question_type || 'text',
      weight: entry.weight || 1.0,
      order_index: questions.length,
      rubric_criteria: [],
    }])
  }

  const handleSaveQuestionToBank = async (question: any) => {
    if (!question.question_text.trim()) {
      setError(t('createInterview.questionTextRequired'))
      return
    }
    try {
      await api.interviews.saveQuestionToBank({
        question_text: question.question_text,
        expected_answer: question.expected_answer || '',
        question_type: question.question_type || 'text',
        options: question.options || null,
        weight: question.weight || 1.0,
      })
      setError('')
      loadQuestionBank()
    } catch (err: any) {
      setError(err.response?.data?.detail || t('createInterview.saveFailed'))
    }
  }

  const handleDeleteFromBank = async (entryId: number) => {
    try {
      await api.interviews.deleteQuestionBankEntry(entryId)
      setBankEntries(bankEntries.filter((entry) => entry.id !== entryId))
    } catch (err: any) {
      setError(err.response?.data?.detail || t('createInterview.deleteFailed'))
    }
  }
  
  return (
    <div>
      <PageHeader title={t('createInterview.title')} subtitle={t('createInterview.subtitle')} />
      
      <ErrorAlert message={error} onClose={() => setError('')} />

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">
            <FiLayers className="me-2" />
            {t('createInterview.startFromTemplate')}
          </h5>
        </Card.Header>
        <Card.Body>
          <Row className="align-items-end">
            <Col md={8}>
              <Form.Group className="mb-3" controlId="interview-template">
                <Form.Label>{t('createInterview.template')}</Form.Label>
                <Form.Select
                  value={selectedTemplateId}
                  onChange={(event) => handleTemplateSelect(event.target.value)}
                >
                  <option value="">{t('createInterview.chooseTemplate')}</option>
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
                {t('createInterview.createFromTemplate')}
              </Button>
            </Col>
          </Row>

          {templateLoading && <p className="mb-0">{t('createInterview.loadingTemplate')}</p>}

          {selectedTemplate && (
            <div>
              <div className="d-flex gap-2 align-items-center mb-2">
                <h6 className="mb-0">{selectedTemplate.name}</h6>
                <Badge bg="secondary">{selectedTemplate.role_category}</Badge>
                <Badge bg="light" text="dark">{t('dashboard.minutesShort', { count: selectedTemplate.duration_minutes })}</Badge>
                <Button
                  type="button"
                  variant="success"
                  size="sm"
                  onClick={handleLoadTemplateQuestions}
                  disabled={!selectedTemplate.questions?.length}
                >
                  <FiPlus className="me-1" />
                  {t('createInterview.loadQuestions')}
                </Button>
              </div>
              <p className="text-muted">{selectedTemplate.description}</p>
              <ol className="mb-0">
                {selectedTemplate.questions.map((question: any) => (
                  <li key={question.id} className="mb-2">
                    <strong>{question.question_text}</strong>
                    <br />
                    <small className="text-muted">{t('interviewDetail.weightX', { weight: question.weight })}</small>
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

      <Card className="mb-4">
        <Card.Header>
          <h5 className="mb-0">
            <FiBookOpen className="me-2" />
            {t('createInterview.questionBank')}
          </h5>
        </Card.Header>
        <Card.Body>
          {bankLoading ? (
            <p className="text-muted mb-0">{t('createInterview.loadingBank')}</p>
          ) : bankEntries.length === 0 ? (
            <p className="text-muted mb-0">
              {t('createInterview.noSavedQuestions')}
            </p>
          ) : (
            <Row>
              {bankEntries.map((entry) => (
                <Col md={6} key={entry.id} className="mb-3">
                  <Card className="bg-light h-100">
                    <Card.Body>
                      <div className="d-flex justify-content-between align-items-start gap-2">
                        <div>
                          <Badge bg="secondary" className="mb-2">{entry.question_type}</Badge>
                          <p className="mb-1">{entry.question_text}</p>
                          <small className="text-muted">
                            {t('interviewDetail.weightX', { weight: entry.weight })}
                            {entry.expected_answer ? t('createInterview.hasReferenceAnswer') : ''}
                          </small>
                        </div>
                        <div className="d-flex gap-1">
                          <Button variant="outline-primary" size="sm" onClick={() => handleAddFromBank(entry)}>
                            <FiPlus /> {t('common.add')}
                          </Button>
                          <Button variant="outline-danger" size="sm" onClick={() => handleDeleteFromBank(entry.id)}>
                            <FiTrash2 />
                          </Button>
                        </div>
                      </div>
                    </Card.Body>
                  </Card>
                </Col>
              ))}
            </Row>
          )}
        </Card.Body>
      </Card>
      
      <Form onSubmit={handleSubmit}>
        <Card className="mb-4">
          <Card.Header>
            <h5 className="mb-0">{t('createInterview.details')}</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={6}>
                <Form.Group className="mb-3" controlId="interview-title">
                  <Form.Label>{t('createInterview.titleRequired')}</Form.Label>
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
                  <Form.Label>{t('createInterview.durationMinutes')}</Form.Label>
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
              <Form.Label>{t('common.description')}</Form.Label>
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
                  <Form.Label>{t('createInterview.maximumAttempts')}</Form.Label>
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
                  <Form.Label>{t('createInterview.passScorePercent')}</Form.Label>
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
        
        <h4 className="mb-3">{t('createInterview.questions')}</h4>
        
        {questions.map((question, index) => (
          <Card key={index} className="mb-3">
            <Card.Header className="d-flex justify-content-between align-items-center">
              <h6 className="mb-0">{t('createInterview.questionN', { n: index + 1 })}</h6>
              <div className="d-flex gap-2">
                <Button
                  variant="outline-primary"
                  size="sm"
                  onClick={() => handleSaveQuestionToBank(question)}
                  disabled={!question.question_text.trim()}
                  title={t('createInterview.saveToBankTooltip')}
                >
                  <FiBookOpen className="me-1" />
                  {t('createInterview.saveToBank')}
                </Button>
                <Button
                  variant="outline-danger"
                  size="sm"
                  onClick={() => removeQuestion(index)}
                  disabled={questions.length === 1}
                >
                  <FiTrash2 />
                </Button>
              </div>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-3" controlId={`question-text-${index}`}>
                <Form.Label>{t('createInterview.questionText')}</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={2}
                  value={question.question_text}
                  onChange={(e) => updateQuestion(index, 'question_text', e.target.value)}
                  required
                />
              </Form.Group>
              
              <Form.Group className="mb-3">
                <Form.Label>{t('createInterview.expectedAnswer')}</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={question.expected_answer}
                  onChange={(e) => updateQuestion(index, 'expected_answer', e.target.value)}
                  placeholder={t('createInterview.expectedAnswerPlaceholder')}
                />
              </Form.Group>
              
              <Row>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>{t('createInterview.questionType')}</Form.Label>
                    <Form.Select
                      value={question.question_type}
                      onChange={(e) => updateQuestion(index, 'question_type', e.target.value)}
                    >
                      <option value="text">{t('createInterview.textVoice')}</option>
                      <option value="multiple_choice">{t('createInterview.multipleChoice')}</option>
                      <option value="coding">{t('createInterview.coding')}</option>
                    </Form.Select>
                  </Form.Group>
                </Col>
                <Col md={6}>
                  <Form.Group className="mb-3">
                    <Form.Label>{t('createInterview.weightImportance')}</Form.Label>
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
                  <h6 className="mb-0">{t('createInterview.rubricCriteria')}</h6>
                  <Button
                    type="button"
                    variant="outline-secondary"
                    size="sm"
                    onClick={() => addRubricCriterion(index)}
                  >
                    <FiPlus className="me-1" />
                    {t('interviewDetail.addCriterion')}
                  </Button>
                </div>

                {(question.rubric_criteria || []).length === 0 ? (
                  <p className="text-muted mb-0">{t('createInterview.noCriteria')}</p>
                ) : (
                  question.rubric_criteria.map((criterion: any, criterionIndex: number) => (
                    <Card key={criterionIndex} className="mb-3 bg-light">
                      <Card.Body>
                        <div className="d-flex justify-content-between align-items-start gap-2 mb-3">
                          <strong>{t('createInterview.criterionN', { n: criterionIndex + 1 })}</strong>
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
                              <Form.Label>{t('common.name')}</Form.Label>
                              <Form.Control
                                value={criterion.name}
                                onChange={(event) => updateRubricCriterion(index, criterionIndex, 'name', event.target.value)}
                                placeholder={t('createInterview.criterionNamePlaceholder')}
                              />
                            </Form.Group>
                          </Col>
                          <Col md={4}>
                            <Form.Group className="mb-3" controlId={`rubric-weight-${index}-${criterionIndex}`}>
                              <Form.Label>{t('common.weight')}</Form.Label>
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
                          <Form.Label>{t('common.description')}</Form.Label>
                          <Form.Control
                            as="textarea"
                            rows={2}
                            value={criterion.description}
                            onChange={(event) => updateRubricCriterion(index, criterionIndex, 'description', event.target.value)}
                            placeholder={t('createInterview.criterionPlaceholder')}
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
          {t('createInterview.addQuestion')}
        </Button>
        
        <div className="d-flex gap-2">
          <Button variant="primary" type="submit" disabled={loading}>
            <FiSave className="me-2" />
            {loading ? t('createInterview.creating') : t('createInterview.create')}
          </Button>
          <Button variant="secondary" onClick={() => navigate(-1)}>
            {t('common.cancel')}
          </Button>
        </div>
      </Form>
    </div>
  )
}

export default CreateInterview
