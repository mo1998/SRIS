import React, { useEffect, useState, useRef } from 'react'
import { Container, Row, Col, Card, Button, Alert, ProgressBar, Form } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import Webcam from 'react-webcam'
import { api } from '../services/api'
import { FiMic, FiMicOff, FiVideo, FiVideoOff, FiCheck, FiArrowRight } from 'react-icons/fi'

const InterviewRoom: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const webcamRef = useRef<Webcam>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  
  const [invitation, setInvitation] = useState<any>(null)
  const [interview, setInterview] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [responseId, setResponseId] = useState<number | null>(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answerText, setAnswerText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [audioChunks, setAudioChunks] = useState<Blob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'setup' | 'interview' | 'complete'>('setup')
  
  // Quality metrics
  const [qualityMetrics, setQualityMetrics] = useState({
    voice: 0,
    background: 0,
    face: 0,
    lighting: 0
  })
  const [isMicOn, setIsMicOn] = useState(true)
  const [isCameraOn, setIsCameraOn] = useState(true)
  
  // Emotion detection
  const [currentEmotion, setCurrentEmotion] = useState('neutral')
  const [emotionTimeline, setEmotionTimeline] = useState<any[]>([])
  
  useEffect(() => {
    verifyInvitation()
  }, [token])
  
  const verifyInvitation = async () => {
    try {
      const invResponse = await api.invitations.verify(token!)
      setInvitation(invResponse.data)
      
      const interviewResponse = await api.interviews.get(invResponse.data.interview_id)
      setInterview(interviewResponse.data)
      
      const questionsResponse = await api.interviews.getQuestions(invResponse.data.interview_id)
      setQuestions(questionsResponse.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid invitation')
    } finally {
      setLoading(false)
    }
  }
  
  const startInterview = async () => {
    try {
      const response = await api.responses.start({
        interview_id: invitation.interview_id,
        candidate_email: invitation.candidate_email,
        candidate_name: invitation.candidate_name,
        invitation_token: token
      })
      
      setResponseId(response.data.id)
      setStep('interview')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start interview')
    }
  }
  
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      
      const chunks: Blob[] = []
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data)
        }
      }
      
      mediaRecorder.onstop = () => {
        setAudioChunks(chunks)
        stream.getTracks().forEach(track => track.stop())
      }
      
      mediaRecorder.start()
      setIsRecording(true)
    } catch (err) {
      console.error('Failed to start recording:', err)
    }
  }
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }
  
  const submitAnswer = async () => {
    if (!responseId) return
    
    const currentQuestion = questions[currentQuestionIndex]
    let audioBlob: File | undefined
    
    if (audioChunks.length > 0) {
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      audioBlob = new File([blob], `answer_${currentQuestion.id}.webm`)
    }
    
    try {
      await api.responses.submitAnswer(
        responseId,
        currentQuestion.id,
        answerText,
        audioBlob
      )
      
      setAnswerText('')
      setAudioChunks([])
      
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1)
      } else {
        await completeInterview()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit answer')
    }
  }
  
  const completeInterview = async () => {
    if (!responseId) return
    
    try {
      // Submit quality metrics
      await api.responses.submitQuality(responseId, {
        voice_quality: qualityMetrics.voice,
        background_quality: qualityMetrics.background,
        face_visibility: qualityMetrics.face,
        lighting: qualityMetrics.lighting,
        recommendations: []
      })
      
      // Submit emotion data
      await api.responses.submitEmotion(responseId, {
        emotion: currentEmotion,
        confidence: qualityMetrics.face,
        timeline: emotionTimeline
      })
      
      // Complete
      await api.responses.complete(responseId)
      setStep('complete')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete interview')
    }
  }
  
  // Simulate quality checks (in production, use real AI models)
  useEffect(() => {
    if (step !== 'interview') return
    
    const interval = setInterval(() => {
      // Simulated quality metrics
      setQualityMetrics({
        voice: 85 + Math.random() * 10,
        background: 80 + Math.random() * 15,
        face: 90 + Math.random() * 10,
        lighting: 75 + Math.random() * 20
      })
      
      // Simulated emotions
      const emotions = ['confident', 'neutral', 'happy', 'nervous', 'focused']
      const newEmotion = emotions[Math.floor(Math.random() * emotions.length)]
      setCurrentEmotion(newEmotion)
      setEmotionTimeline(prev => [...prev, { emotion: newEmotion, timestamp: Date.now() / 1000 }])
    }, 5000)
    
    return () => clearInterval(interval)
  }, [step])
  
  const getQualityColor = (score: number) => {
    if (score >= 80) return 'success'
    if (score >= 60) return 'warning'
    return 'danger'
  }
  
  if (loading) {
    return <Container className="mt-5"><p>Loading interview...</p></Container>
  }
  
  if (error && !invitation) {
    return (
      <Container className="mt-5">
        <Alert variant="danger">{error}</Alert>
        <Button onClick={() => navigate('/login')}>Go to Login</Button>
      </Container>
    )
  }
  
  if (step === 'setup') {
    return (
      <Container className="mt-5">
        <Card className="max-w-2xl mx-auto">
          <Card.Body className="text-center">
            <h1 className="mb-4">{interview?.title}</h1>
            <p className="lead">{interview?.description}</p>
            
            <Card className="mb-4 bg-light">
              <Card.Body>
                <h5>Interview Instructions</h5>
                <ul className="text-start">
                  <li>Find a quiet place with good lighting</li>
                  <li>Ensure your face is clearly visible</li>
                  <li>Speak clearly when answering questions</li>
                  <li>You can record your answers with the microphone</li>
                  <li>The AI will evaluate your responses</li>
                </ul>
              </Card.Body>
            </Card>
            
            <Row className="mb-4">
              <Col>
                <h6>Duration: {interview?.duration_minutes} minutes</h6>
                <h6>Questions: {questions.length}</h6>
              </Col>
            </Row>
            
            <Button variant="primary" size="lg" onClick={startInterview}>
              Start Interview
            </Button>
          </Card.Body>
        </Card>
      </Container>
    )
  }
  
  if (step === 'complete') {
    return (
      <Container className="mt-5">
        <Card className="max-w-2xl mx-auto text-center">
          <Card.Body>
            <FiCheck className="text-success mb-3" size={64} />
            <h1>Interview Completed!</h1>
            <p className="lead">Thank you for completing the interview.</p>
            <p>Your responses have been recorded and will be evaluated by the AI system.</p>
            <p>The employer will review your results and contact you if you move forward.</p>
            <Button variant="primary" onClick={() => navigate('/login')}>
              Go to Login
            </Button>
          </Card.Body>
        </Card>
      </Container>
    )
  }
  
  const currentQuestion = questions[currentQuestionIndex]
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100
  
  return (
    <Container fluid className="mt-3">
      <Row>
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Question {currentQuestionIndex + 1} of {questions.length}</h5>
                <ProgressBar now={progress} style={{ width: '200px' }} />
              </div>
            </Card.Header>
            <Card.Body>
              <h4 className="mb-4">{currentQuestion?.question_text}</h4>
              
              <Form.Group className="mb-3">
                <Form.Label>Your Answer</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={6}
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Type your answer here or record audio..."
                />
              </Form.Group>
              
              <div className="d-flex gap-2 mb-3">
                <Button
                  variant={isRecording ? 'danger' : 'outline-primary'}
                  onClick={isRecording ? stopRecording : startRecording}
                >
                  {isRecording ? <FiMicOff className="me-2" /> : <FiMic className="me-2" />}
                  {isRecording ? 'Stop Recording' : 'Record Audio'}
                </Button>
              </div>
              
              <div className="d-flex justify-content-between">
                <Button
                  variant="secondary"
                  disabled={currentQuestionIndex === 0}
                  onClick={() => setCurrentQuestionIndex(currentQuestionIndex - 1)}
                >
                  Previous
                </Button>
                <Button variant="primary" onClick={submitAnswer}>
                  {currentQuestionIndex < questions.length - 1 ? (
                    <>
                      Next <FiArrowRight className="ms-2" />
                    </>
                  ) : (
                    'Submit & Complete'
                  )}
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">Video & Audio</h6>
            </Card.Header>
            <Card.Body>
              <Webcam
                ref={webcamRef}
                audio={false}
                videoConstraints={{
                  facingMode: 'user'
                }}
                style={{ width: '100%', borderRadius: '8px' }}
                disabled={!isCameraOn}
              />
              
              <div className="d-flex gap-2 mt-3">
                <Button
                  size="sm"
                  variant={isCameraOn ? 'outline-primary' : 'outline-secondary'}
                  onClick={() => setIsCameraOn(!isCameraOn)}
                >
                  {isCameraOn ? <FiVideo /> : <FiVideoOff />}
                </Button>
                <Button
                  size="sm"
                  variant={isMicOn ? 'outline-primary' : 'outline-secondary'}
                  onClick={() => setIsMicOn(!isMicOn)}
                >
                  {isMicOn ? <FiMic /> : <FiMicOff />}
                </Button>
              </div>
            </Card.Body>
          </Card>
          
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">Quality Metrics</h6>
            </Card.Header>
            <Card.Body>
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <small>Voice Quality</small>
                  <small>{qualityMetrics.voice.toFixed(1)}%</small>
                </div>
                <ProgressBar now={qualityMetrics.voice} variant={getQualityColor(qualityMetrics.voice)} />
              </div>
              
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <small>Background</small>
                  <small>{qualityMetrics.background.toFixed(1)}%</small>
                </div>
                <ProgressBar now={qualityMetrics.background} variant={getQualityColor(qualityMetrics.background)} />
              </div>
              
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <small>Face Visibility</small>
                  <small>{qualityMetrics.face.toFixed(1)}%</small>
                </div>
                <ProgressBar now={qualityMetrics.face} variant={getQualityColor(qualityMetrics.face)} />
              </div>
              
              <div className="mb-3">
                <div className="d-flex justify-content-between mb-1">
                  <small>Lighting</small>
                  <small>{qualityMetrics.lighting.toFixed(1)}%</small>
                </div>
                <ProgressBar now={qualityMetrics.lighting} variant={getQualityColor(qualityMetrics.lighting)} />
              </div>
            </Card.Body>
          </Card>
          
          <Card>
            <Card.Header>
              <h6 className="mb-0">Detected Emotion</h6>
            </Card.Header>
            <Card.Body className="text-center">
              <h4 className={`text-${currentEmotion === 'confident' || currentEmotion === 'happy' ? 'success' : currentEmotion === 'nervous' ? 'warning' : 'primary'}`}>
                {currentEmotion.charAt(0).toUpperCase() + currentEmotion.slice(1)}
              </h4>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default InterviewRoom
