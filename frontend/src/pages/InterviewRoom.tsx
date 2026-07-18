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
  const [step, setStep] = useState<'verification' | 'setup' | 'interview' | 'complete'>('verification')
  const [privacyAcknowledged, setPrivacyAcknowledged] = useState(false)
  const [participationConsented, setParticipationConsented] = useState(false)
  const [deviceCheckStatus, setDeviceCheckStatus] = useState<'idle' | 'checking' | 'passed' | 'failed'>('idle')
  const [deviceCheckError, setDeviceCheckError] = useState('')
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null)
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const [restoredDraft, setRestoredDraft] = useState(false)
  
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
      const verifiedInvitation = invResponse.data
      setInvitation(verifiedInvitation)
      setInterview(verifiedInvitation.interview)
      setQuestions(verifiedInvitation.interview?.questions || [])
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid invitation')
    } finally {
      setLoading(false)
    }
  }
  
  const startInterview = async () => {
    if (!privacyAcknowledged || !participationConsented) {
      setError('Please review and accept the candidate consent before starting.')
      return
    }

    if (deviceCheckStatus !== 'passed') {
      setError('Please complete the camera and microphone check before starting.')
      return
    }

    try {
      const response = await api.responses.start({
        interview_id: invitation.interview_id,
        candidate_email: invitation.candidate_email,
        candidate_name: invitation.candidate_name,
        invitation_token: token
      })
      
      setResponseId(response.data.id)
      setRemainingSeconds((interview?.duration_minutes || 0) * 60)
      setStep('interview')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start interview')
    }
  }

  const checkDevices = async () => {
    setError('')
    setDeviceCheckError('')
    setDeviceCheckStatus('checking')

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('Camera and microphone access is not available in this browser.')
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true })
      stream.getTracks().forEach((track) => track.stop())
      setIsMicOn(true)
      setIsCameraOn(true)
      setDeviceCheckStatus('passed')
    } catch (err: any) {
      setIsMicOn(false)
      setIsCameraOn(false)
      setDeviceCheckStatus('failed')
      setDeviceCheckError(err.message || 'Allow camera and microphone access to continue.')
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
    const draftKey = getDraftKey(currentQuestion?.id)
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

      if (draftKey) {
        localStorage.removeItem(draftKey)
      }
      
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

  const getDraftKey = (questionId?: number) => questionId && token ? `sris-answer-draft:${token}:${questionId}` : null

  const formatTime = (seconds: number | null) => {
    if (seconds === null) return '--:--'
    const minutes = Math.floor(seconds / 60)
    const remaining = seconds % 60
    return `${minutes}:${remaining.toString().padStart(2, '0')}`
  }

  const currentQuestion = questions[currentQuestionIndex]
  const currentDraftKey = getDraftKey(currentQuestion?.id)
  const progress = questions.length ? ((currentQuestionIndex + 1) / questions.length) * 100 : 0

  useEffect(() => {
    if (step !== 'interview' || !currentDraftKey) return

    const savedAnswer = localStorage.getItem(currentDraftKey)
    setAnswerText(savedAnswer || '')
    setRestoredDraft(Boolean(savedAnswer))
    setLastSavedAt(savedAnswer ? new Date() : null)
  }, [step, currentDraftKey])

  useEffect(() => {
    if (step !== 'interview' || !currentDraftKey) return

    const timeout = window.setTimeout(() => {
      if (answerText.trim()) {
        localStorage.setItem(currentDraftKey, answerText)
        setLastSavedAt(new Date())
      } else {
        localStorage.removeItem(currentDraftKey)
        setLastSavedAt(null)
      }
      setRestoredDraft(false)
    }, 500)

    return () => window.clearTimeout(timeout)
  }, [answerText, step, currentDraftKey])

  useEffect(() => {
    if (step !== 'interview' || remainingSeconds === null) return
    if (remainingSeconds <= 0) return

    const interval = window.setInterval(() => {
      setRemainingSeconds((current) => current === null ? current : Math.max(current - 1, 0))
    }, 1000)

    return () => window.clearInterval(interval)
  }, [step, remainingSeconds])
  
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

  if (step === 'verification') {
    return (
      <Container className="mt-5">
        <Card className="max-w-2xl mx-auto">
          <Card.Body>
            <div className="text-center mb-4">
              <FiCheck className="text-success mb-3" size={56} />
              <h1>Invitation Verified</h1>
              <p className="text-muted mb-0">Review the interview details before continuing.</p>
            </div>

            <Card className="mb-4 bg-light">
              <Card.Body>
                <h5 className="mb-3">{interview?.title}</h5>
                {interview?.description && <p>{interview.description}</p>}
                <Row>
                  <Col sm={6}>
                    <p className="mb-1"><strong>Candidate:</strong> {invitation?.candidate_name}</p>
                    <p className="mb-1"><strong>Email:</strong> {invitation?.candidate_email}</p>
                  </Col>
                  <Col sm={6}>
                    <p className="mb-1"><strong>Duration:</strong> {interview?.duration_minutes} minutes</p>
                    <p className="mb-1"><strong>Questions:</strong> {questions.length}</p>
                    {invitation?.expires_at && (
                      <p className="mb-1"><strong>Expires:</strong> {new Date(invitation.expires_at).toLocaleDateString()}</p>
                    )}
                  </Col>
                </Row>
              </Card.Body>
            </Card>

            <div className="d-flex justify-content-center">
              <Button variant="primary" size="lg" onClick={() => setStep('setup')}>
                Continue to Setup
              </Button>
            </div>
          </Card.Body>
        </Card>
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
            {error && <Alert variant="danger">{error}</Alert>}
            
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

            <Card className="mb-4 text-start">
              <Card.Body>
                <h5>Privacy and Consent</h5>
                <p className="text-muted">
                  Your answers, optional audio, and interview metadata may be stored and reviewed by the employer for this hiring process.
                </p>
                <Form.Check
                  id="privacy-acknowledgement"
                  className="mb-2"
                  type="checkbox"
                  label="I understand how my interview data will be used."
                  checked={privacyAcknowledged}
                  onChange={(event) => setPrivacyAcknowledged(event.target.checked)}
                />
                <Form.Check
                  id="participation-consent"
                  type="checkbox"
                  label="I consent to participate in this remote interview."
                  checked={participationConsented}
                  onChange={(event) => setParticipationConsented(event.target.checked)}
                />
              </Card.Body>
            </Card>

            <Card className="mb-4 text-start">
              <Card.Body>
                <h5>Device Setup</h5>
                <p className="text-muted">
                  Check your camera and microphone before the interview starts. You can still answer with text if you choose not to record audio.
                </p>
                <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
                  <Button type="button" variant="outline-primary" onClick={checkDevices} disabled={deviceCheckStatus === 'checking'}>
                    {deviceCheckStatus === 'checking' ? 'Checking Devices...' : 'Check Camera and Microphone'}
                  </Button>
                  {deviceCheckStatus === 'passed' && <span className="text-success">Camera and microphone are available.</span>}
                  {deviceCheckStatus === 'failed' && <span className="text-danger">Device check failed.</span>}
                </div>
                {deviceCheckError && <Alert variant="warning" className="mb-0">{deviceCheckError}</Alert>}
              </Card.Body>
            </Card>
            
            <Row className="mb-4">
              <Col>
                <h6>Duration: {interview?.duration_minutes} minutes</h6>
                <h6>Questions: {questions.length}</h6>
              </Col>
            </Row>
            
            <Button variant="primary" size="lg" onClick={startInterview} disabled={!privacyAcknowledged || !participationConsented || deviceCheckStatus !== 'passed'}>
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
  
  return (
    <Container fluid className="mt-3">
      <Row>
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <div>
                  <h5 className="mb-1">Question {currentQuestionIndex + 1} of {questions.length}</h5>
                  <small className="text-muted">Time remaining: {formatTime(remainingSeconds)}</small>
                </div>
                <ProgressBar now={progress} label={`${Math.round(progress)}%`} style={{ width: '220px' }} />
              </div>
            </Card.Header>
            <Card.Body>
              {remainingSeconds === 0 && (
                <Alert variant="warning">Time is up. Submit your current answer to complete the interview.</Alert>
              )}
              {restoredDraft && <Alert variant="info">Your saved draft was restored on this question.</Alert>}
              <h4 className="mb-4">{currentQuestion?.question_text}</h4>
              
              <Form.Group className="mb-3" controlId="candidate-answer-text">
                <Form.Label>Your Answer</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={6}
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Type your answer here or record audio..."
                />
                <Form.Text className="text-muted">
                  {lastSavedAt ? `Draft saved locally at ${lastSavedAt.toLocaleTimeString()}` : 'Your typed answer is saved locally while you work.'}
                </Form.Text>
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
