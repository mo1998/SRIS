import React, { useEffect, useState, useRef } from 'react'
import { Container, Row, Col, Card, Button, Alert, ProgressBar, Form } from 'react-bootstrap'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Webcam from 'react-webcam'
import { api } from '../services/api'
import LanguageSwitcher from '../i18n/LanguageSwitcher'
import { FiMic, FiMicOff, FiVideo, FiVideoOff, FiCheck, FiArrowRight, FiCamera } from 'react-icons/fi'

const InterviewRoom: React.FC = () => {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const webcamRef = useRef<Webcam>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const videoRecorderRef = useRef<MediaRecorder | null>(null)
  
  const [invitation, setInvitation] = useState<any>(null)
  const [interview, setInterview] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [responseId, setResponseId] = useState<number | null>(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answerText, setAnswerText] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const [audioChunks, setAudioChunks] = useState<Blob[]>([])
  const [isVideoRecording, setIsVideoRecording] = useState(false)
  const [videoChunks, setVideoChunks] = useState<Blob[]>([])
  const [videoPreviewUrl, setVideoPreviewUrl] = useState<string | null>(null)
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
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [answerError, setAnswerError] = useState('')
  const [isMicOn, setIsMicOn] = useState(true)
  const [isCameraOn, setIsCameraOn] = useState(true)
  
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
      setError(err.response?.data?.detail || t('interviewRoom.invalidInvitation'))
    } finally {
      setLoading(false)
    }
  }
  
  const startInterview = async () => {
    if (!privacyAcknowledged || !participationConsented) {
      setError(t('interviewRoom.consentFirst'))
      return
    }

    if (deviceCheckStatus !== 'passed') {
      setError(t('interviewRoom.deviceFirst'))
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
      syncServerTimer(response.data.id)
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewRoom.startFailed'))
    }
  }

  const syncServerTimer = async (id: number) => {
    try {
      const timerRes = await api.responses.getTimer(id)
      const timer = timerRes.data
      const serverNow = new Date(timer.server_time).getTime()
      const clientNow = Date.now()
      const clockSkew = clientNow - serverNow
      const deadlineMs = new Date(timer.deadline).getTime() + clockSkew
      setRemainingSeconds(Math.max(0, Math.round((deadlineMs - Date.now()) / 1000)))
    } catch (err) {
      console.error('Failed to sync server timer:', err)
    }
  }

  const checkDevices = async () => {
    setError('')
    setDeviceCheckError('')
    setDeviceCheckStatus('checking')

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(t('interviewRoom.noMedia'))
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
      setDeviceCheckError(err.message || t('interviewRoom.allowAccess'))
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

  const startVideoRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true })
      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp9,opus')
        ? 'video/webm;codecs=vp9,opus'
        : MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm'
      const mediaRecorder = new MediaRecorder(stream, { mimeType })
      videoRecorderRef.current = mediaRecorder

      const chunks: Blob[] = []
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' })
        setVideoChunks(chunks)
        setVideoPreviewUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach(track => track.stop())
      }

      mediaRecorder.start()
      setIsVideoRecording(true)
    } catch (err) {
      console.error('Failed to start video recording:', err)
    }
  }

  const stopVideoRecording = () => {
    if (videoRecorderRef.current && videoRecorderRef.current.state !== 'inactive') {
      videoRecorderRef.current.stop()
      setIsVideoRecording(false)
    }
  }

  const clearVideo = () => {
    if (videoPreviewUrl) {
      URL.revokeObjectURL(videoPreviewUrl)
    }
    setVideoChunks([])
    setVideoPreviewUrl(null)
  }
  
  const submitAnswer = async () => {
    if (!responseId || isSubmittingAnswer) return
    
    const currentQuestion = questions[currentQuestionIndex]
    const draftKey = getDraftKey(currentQuestion?.id)
    let audioBlob: File | undefined
    let videoBlob: File | undefined
    
    if (audioChunks.length > 0) {
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      audioBlob = new File([blob], `answer_${currentQuestion.id}.webm`)
    }
    
    if (videoChunks.length > 0) {
      const blob = new Blob(videoChunks, { type: 'video/webm' })
      videoBlob = new File([blob], `answer_${currentQuestion.id}.webm`)
    }

    setError('')
    setAnswerError('')
    setUploadProgress(audioBlob || videoBlob ? 0 : 100)
    setIsSubmittingAnswer(true)
    
    try {
      await api.responses.submitAnswer(
        responseId,
        currentQuestion.id,
        answerText,
        audioBlob,
        videoBlob,
        undefined,
        (progressEvent: any) => {
          if (!progressEvent.total) {
            setUploadProgress(100)
            return
          }
          setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total))
        }
      )

      if (draftKey) {
        localStorage.removeItem(draftKey)
      }
      
      setAnswerText('')
      setAudioChunks([])
      clearVideo()
      
      if (currentQuestionIndex < questions.length - 1) {
        setCurrentQuestionIndex(currentQuestionIndex + 1)
      } else {
        await completeInterview()
      }
    } catch (err: any) {
      setAnswerError(err.response?.data?.detail || t('interviewRoom.submitFailed'))
    } finally {
      setIsSubmittingAnswer(false)
    }
  }
  
  const completeInterview = async () => {
    if (!responseId) return
    
    try {
      await api.responses.complete(responseId)
      setStep('complete')
    } catch (err: any) {
      setError(err.response?.data?.detail || t('interviewRoom.completeFailed'))
    }
  }

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

  // Re-sync the countdown with the server periodically so a tampered client
  // clock cannot silently extend the interview.
  useEffect(() => {
    if (step !== 'interview' || !responseId) return

    const sync = window.setInterval(() => syncServerTimer(responseId), 30000)
    return () => window.clearInterval(sync)
  }, [step, responseId])

  // Auto-submit the current answer and complete when time runs out. Reset the
  // guard when the question advances so remaining answers auto-submit too.
  const autoSubmittedRef = useRef(false)
  useEffect(() => {
    autoSubmittedRef.current = false
  }, [currentQuestionIndex])

  useEffect(() => {
    if (step !== 'interview' || remainingSeconds !== 0) return
    if (autoSubmittedRef.current || isSubmittingAnswer) return

    autoSubmittedRef.current = true
    submitAnswer()
  }, [step, remainingSeconds, isSubmittingAnswer])

  // Track integrity events (tab switches / window blurs) during the interview
  useEffect(() => {
    if (step !== 'interview' || !responseId) return

    const events: any[] = []
    let flushTimer: number | undefined

    const flush = () => {
      if (events.length === 0 || !responseId) return
      const batch = events.splice(0, events.length)
      api.responses
        .submitIntegrityEvents(responseId, batch)
        .catch(() => {})
    }

    const record = (eventType: string, details?: string) => {
      events.push({ event_type: eventType, details: details || '' })
    }

    const onVisibility = () => {
      if (document.hidden) record('tab_hidden')
      else record('tab_visible')
    }
    const onBlur = () => record('window_blur')
    const onFocus = () => record('window_focus')

    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', onBlur)
    window.addEventListener('focus', onFocus)
    flushTimer = window.setInterval(flush, 10000)

    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', onBlur)
      window.removeEventListener('focus', onFocus)
      if (flushTimer) window.clearInterval(flushTimer)
      flush()
    }
  }, [step, responseId])

  if (loading) {
    return <Container className="mt-5"><p>{t('interviewRoom.loading')}</p></Container>
  }
  
  if (error && !invitation) {
    return (
      <Container className="mt-5">
        <Alert variant="danger">{error}</Alert>
        <Button onClick={() => navigate('/login')}>{t('interviewRoom.goToLogin')}</Button>
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
              <h1>{t('interviewRoom.verified')}</h1>
              <p className="text-muted mb-0">{t('interviewRoom.reviewDetails')}</p>
            </div>

            <Card className="mb-4 bg-light">
              <Card.Body>
                <h5 className="mb-3">{interview?.title}</h5>
                {interview?.description && <p>{interview.description}</p>}
                <Row>
                  <Col sm={6}>
                    <p className="mb-1"><strong>{t('interviewRoom.candidate')}</strong> {invitation?.candidate_name}</p>
                    <p className="mb-1"><strong>{t('common.email')}:</strong> {invitation?.candidate_email}</p>
                  </Col>
                  <Col sm={6}>
                    <p className="mb-1"><strong>{t('interviewRoom.duration')}</strong> {t('interviewRoom.minutes', { count: interview?.duration_minutes })}</p>
                    <p className="mb-1"><strong>{t('interviewRoom.questions')}</strong> {questions.length}</p>
                    {invitation?.expires_at && (
                      <p className="mb-1"><strong>{t('interviewRoom.expires')}</strong> {new Date(invitation.expires_at).toLocaleDateString()}</p>
                    )}
                  </Col>
                </Row>
              </Card.Body>
            </Card>

            <div className="d-flex justify-content-center">
              <Button variant="primary" size="lg" onClick={() => setStep('setup')}>
                {t('interviewRoom.continueToSetup')}
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
                <h5>{t('interviewRoom.instructionsTitle')}</h5>
                <ul className="text-start">
                  <li>{t('interviewRoom.instructionQuiet')}</li>
                  <li>{t('interviewRoom.instructionFace')}</li>
                  <li>{t('interviewRoom.instructionSpeak')}</li>
                  <li>{t('interviewRoom.instructionRecord')}</li>
                  <li>{t('interviewRoom.instructionAI')}</li>
                </ul>
              </Card.Body>
            </Card>

            <Card className="mb-4 text-start">
              <Card.Body>
                <h5>{t('interviewRoom.privacyTitle')}</h5>
                <p className="text-muted">
                  {t('interviewRoom.privacyText')}
                </p>
                <Form.Check
                  id="privacy-acknowledgement"
                  className="mb-2"
                  type="checkbox"
                  label={t('interviewRoom.understandDataUse')}
                  checked={privacyAcknowledged}
                  onChange={(event) => setPrivacyAcknowledged(event.target.checked)}
                />
                <Form.Check
                  id="participation-consent"
                  type="checkbox"
                  label={t('interviewRoom.consentParticipate')}
                  checked={participationConsented}
                  onChange={(event) => setParticipationConsented(event.target.checked)}
                />
              </Card.Body>
            </Card>

            <Card className="mb-4 text-start">
              <Card.Body>
                <h5>{t('interviewRoom.deviceTitle')}</h5>
                <p className="text-muted">
                  {t('interviewRoom.deviceText')}
                </p>
                <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
                  <Button type="button" variant="outline-primary" onClick={checkDevices} disabled={deviceCheckStatus === 'checking'}>
                    {deviceCheckStatus === 'checking' ? t('interviewRoom.checkingDevices') : t('interviewRoom.checkDevices')}
                  </Button>
                  {deviceCheckStatus === 'passed' && <span className="text-success">{t('interviewRoom.devicesAvailable')}</span>}
                  {deviceCheckStatus === 'failed' && <span className="text-danger">{t('interviewRoom.deviceFailed')}</span>}
                </div>
                {deviceCheckError && <Alert variant="warning" className="mb-0">{deviceCheckError}</Alert>}
              </Card.Body>
            </Card>
            
            <Row className="mb-4">
              <Col>
                <h6>{t('interviewRoom.durationLine', { count: interview?.duration_minutes })}</h6>
                <h6>{t('interviewRoom.questionsLine', { count: questions.length })}</h6>
              </Col>
            </Row>
            
            <Button variant="primary" size="lg" onClick={startInterview} disabled={!privacyAcknowledged || !participationConsented || deviceCheckStatus !== 'passed'}>
              {t('interviewRoom.start')}
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
            <h1>{t('interviewRoom.completeTitle')}</h1>
            <p className="lead">{t('interviewRoom.thankYou')}</p>
            <p>{t('interviewRoom.recorded')}</p>
            <p>{t('interviewRoom.employerReview')}</p>
            <Button variant="primary" onClick={() => navigate('/login')}>
              {t('interviewRoom.goToLogin')}
            </Button>
          </Card.Body>
        </Card>
      </Container>
    )
  }
  
  return (
    <Container fluid className="mt-3">
      <div style={{ position: 'fixed', top: '0.75rem', right: '0.75rem', zIndex: 1100 }}>
        <LanguageSwitcher />
      </div>
      <Row className="gy-3">
        <Col lg={8}>
          <Card className="mb-4">
            <Card.Header>
              <div className="d-flex flex-column flex-md-row gap-2 justify-content-between align-items-md-center">
                <div>
                  <h5 className="mb-1">{t('interviewRoom.questionOf', { current: currentQuestionIndex + 1, total: questions.length })}</h5>
                  <small className="text-muted">{t('interviewRoom.timeRemaining', { time: formatTime(remainingSeconds) })}</small>
                </div>
                <ProgressBar className="w-100" now={progress} label={`${Math.round(progress)}%`} style={{ maxWidth: '220px' }} />
              </div>
            </Card.Header>
            <Card.Body>
              {error && <Alert variant="danger">{error}</Alert>}
              {answerError && <Alert variant="danger">{answerError}</Alert>}
              {remainingSeconds === 0 && (
                <Alert variant="warning">{t('interviewRoom.timeUp')}</Alert>
              )}
              {restoredDraft && <Alert variant="info">{t('interviewRoom.draftRestored')}</Alert>}
              <h4 className="mb-4">{currentQuestion?.question_text}</h4>
              
              <Form.Group className="mb-3" controlId="candidate-answer-text">
                <Form.Label>{t('interviewRoom.yourAnswer')}</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={6}
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder={t('interviewRoom.answerPlaceholder')}
                />
                <Form.Text className="text-muted">
                  {lastSavedAt ? t('interviewRoom.draftSavedAt', { time: lastSavedAt.toLocaleTimeString() }) : t('interviewRoom.draftSavedNote')}
                </Form.Text>
              </Form.Group>
              
              <div className="d-flex gap-2 mb-3">
                <Button
                  variant={isRecording ? 'danger' : 'outline-primary'}
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={isSubmittingAnswer || isVideoRecording}
                >
                  {isRecording ? <FiMicOff className="me-2" /> : <FiMic className="me-2" />}
                  {isRecording ? t('interviewRoom.stopAudio') : t('interviewRoom.recordAudio')}
                </Button>
                <Button
                  variant={isVideoRecording ? 'danger' : 'outline-secondary'}
                  onClick={isVideoRecording ? stopVideoRecording : startVideoRecording}
                  disabled={isSubmittingAnswer || isRecording}
                >
                  {isVideoRecording ? <FiVideoOff className="me-2" /> : <FiCamera className="me-2" />}
                  {isVideoRecording ? t('interviewRoom.stopVideo') : t('interviewRoom.recordVideo')}
                </Button>
                {videoPreviewUrl && !isVideoRecording && (
                  <Button variant="outline-danger" size="sm" onClick={clearVideo}>
                    {t('interviewRoom.removeVideo')}
                  </Button>
                )}
              </div>
              {audioChunks.length > 0 && <Alert variant="info">{t('interviewRoom.audioReady')}</Alert>}
              {videoPreviewUrl && !isVideoRecording && (
                <div className="mb-3">
                  <video src={videoPreviewUrl} controls style={{ width: '100%', maxHeight: 320, borderRadius: 8 }} />
                </div>
              )}
              {isSubmittingAnswer && (
                <div className="mb-3">
                  <div className="d-flex justify-content-between mb-1">
                    <small>{t('interviewRoom.submitting')}</small>
                    <small>{uploadProgress}%</small>
                  </div>
                  <ProgressBar now={uploadProgress} />
                </div>
              )}
              
              <div className="d-flex flex-column flex-sm-row gap-2 justify-content-between">
                <Button
                  variant="secondary"
                  disabled={currentQuestionIndex === 0}
                  onClick={() => setCurrentQuestionIndex(currentQuestionIndex - 1)}
                >
                  {t('interviewRoom.previous')}
                </Button>
                <Button variant="primary" onClick={submitAnswer} disabled={isSubmittingAnswer || (!answerText.trim() && audioChunks.length === 0 && videoChunks.length === 0)}>
                  {currentQuestionIndex < questions.length - 1 ? (
                    <>
                      {answerError ? t('interviewRoom.retry') : t('interviewRoom.next')} <FiArrowRight className="ms-2" />
                    </>
                  ) : (
                    answerError ? t('interviewRoom.retry') : t('interviewRoom.submitComplete')
                  )}
                </Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
        
        <Col lg={4}>
          <Card className="mb-4">
            <Card.Header>
              <h6 className="mb-0">{t('interviewRoom.videoAudio')}</h6>
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
          
          <Card>
            <Card.Header>
              <h6 className="mb-0">{t('interviewRoom.deviceStatus')}</h6>
            </Card.Header>
            <Card.Body>
              <p className="mb-2"><strong>{t('interviewRoom.camera')}</strong> {isCameraOn ? t('interviewRoom.available') : t('interviewRoom.unavailable')}</p>
              <p className="mb-0"><strong>{t('interviewRoom.microphone')}</strong> {isMicOn ? t('interviewRoom.available') : t('interviewRoom.unavailable')}</p>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default InterviewRoom
