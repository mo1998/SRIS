import React, { useEffect, useRef, useState } from 'react'
import { Container, Card, Button, Alert, Row, Col } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import Webcam from 'react-webcam'
import { FiVideo, FiVideoOff, FiRefreshCw, FiCheck, FiArrowRight, FiPlay, FiStopCircle } from 'react-icons/fi'

export const PRACTICE_SECONDS = 120

type PracticeStage = 'ready' | 'recording' | 'preview'

interface PracticeModeProps {
  onExit: () => void
}

const PracticeMode: React.FC<PracticeModeProps> = ({ onExit }) => {
  const { t } = useTranslation()
  const webcamRef = useRef<Webcam>(null)
  const videoRecorderRef = useRef<MediaRecorder | null>(null)

  const [stage, setStage] = useState<PracticeStage>('ready')
  const [error, setError] = useState('')
  const [remaining, setRemaining] = useState(PRACTICE_SECONDS)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  const stopCamera = () => {
    const stream = webcamRef.current?.stream
    stream?.getTracks().forEach((track) => track.stop())
  }

  useEffect(() => {
    return () => stopCamera()
  }, [])

  useEffect(() => {
    if (stage !== 'recording') return
    if (remaining <= 0) {
      stopRecording()
      return
    }
    const interval = window.setInterval(() => setRemaining((s) => Math.max(s - 1, 0)), 1000)
    return () => window.clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, remaining])

  const startRecording = async () => {
    setError('')
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
        if (e.data.size > 0) chunks.push(e.data)
      }
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' })
        setPreviewUrl(URL.createObjectURL(blob))
        stream.getTracks().forEach((track) => track.stop())
      }

      mediaRecorder.start()
      setStage('recording')
    } catch (err: any) {
      setError(err.message || t('practiceMode.recordFailed'))
    }
  }

  const stopRecording = () => {
    if (videoRecorderRef.current && videoRecorderRef.current.state !== 'inactive') {
      videoRecorderRef.current.stop()
    }
    setStage('preview')
  }

  const reset = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    setPreviewUrl(null)
    setRemaining(PRACTICE_SECONDS)
    setError('')
    setStage('ready')
  }

  const done = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
    stopCamera()
    onExit()
  }

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60)
    const rest = seconds % 60
    return `${minutes}:${rest.toString().padStart(2, '0')}`
  }

  return (
    <Container className="mt-4">
      <Card className="max-w-3xl mx-auto">
        <Card.Body>
          <div className="d-flex flex-column flex-md-row gap-2 justify-content-between align-items-md-center mb-3">
            <div>
              <h1 className="mb-1">{t('practiceMode.title')}</h1>
              <p className="text-muted mb-0">{t('practiceMode.subtitle')}</p>
            </div>
            {stage === 'recording' && (
              <span className="badge bg-danger fs-6">
                {t('practiceMode.recording')} · {formatTime(remaining)}
              </span>
            )}
          </div>

          {error && <Alert variant="danger">{error}</Alert>}

          <Card className="mb-3 bg-light">
            <Card.Body>
              <h5 className="mb-1">{t('practiceMode.sampleLabel')}</h5>
              <p className="mb-0 fs-5">{t('practiceMode.sampleQuestion')}</p>
            </Card.Body>
          </Card>

          <Row className="g-3 mb-3">
            <Col md={7}>
              {stage !== 'preview' ? (
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  videoConstraints={{ facingMode: 'user' }}
                  style={{ width: '100%', borderRadius: 8 }}
                  mirrored
                />
              ) : (
                previewUrl && <video src={previewUrl} controls style={{ width: '100%', borderRadius: 8 }} />
              )}
            </Col>
            <Col md={5}>
              <Card className="h-100">
                <Card.Body className="d-flex flex-column justify-content-between h-100">
                  <div>
                    <h6>{t('practiceMode.whyTitle')}</h6>
                    <ul className="small text-muted ps-3">
                      <li>{t('practiceMode.whyHardware')}</li>
                      <li>{t('practiceMode.whyPace')}</li>
                      <li>{t('practiceMode.whyPrivate')}</li>
                    </ul>
                  </div>
                  <div className="d-flex flex-column gap-2">
                    {stage === 'ready' && (
                      <Button variant="primary" onClick={startRecording}>
                        <FiPlay className="me-2" />
                        {t('practiceMode.startRecording')}
                      </Button>
                    )}
                    {stage === 'recording' && (
                      <Button variant="danger" onClick={stopRecording}>
                        <FiStopCircle className="me-2" />
                        {t('practiceMode.stopRecording')}
                      </Button>
                    )}
                    {stage === 'preview' && (
                      <>
                        <Button variant="outline-primary" onClick={reset}>
                          <FiRefreshCw className="me-2" />
                          {t('practiceMode.tryAgain')}
                        </Button>
                        <Button variant="success" onClick={done}>
                          <FiCheck className="me-2" />
                          {t('practiceMode.gotIt')}
                        </Button>
                      </>
                    )}
                  </div>
                </Card.Body>
              </Card>
            </Col>
          </Row>

          <div className="d-flex justify-content-between align-items-center">
            <p className="text-muted small mb-0">{t('practiceMode.noRecordStored')}</p>
            <Button variant="secondary" onClick={done}>
              <FiArrowRight className="me-2" />
              {t('practiceMode.backToSetup')}
            </Button>
          </div>
        </Card.Body>
      </Card>
    </Container>
  )
}

export default PracticeMode