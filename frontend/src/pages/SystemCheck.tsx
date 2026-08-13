import React, { useEffect, useRef, useState } from 'react'
import { Container, Card, Button, Row, Col, Alert, Spinner } from 'react-bootstrap'
import { useTranslation } from 'react-i18next'
import Webcam from 'react-webcam'
import { FiCheck, FiX, FiCamera, FiMic, FiWifi, FiRefreshCw, FiArrowRight } from 'react-icons/fi'
import { api } from '../services/api'

export const NETWORK_THRESHOLDS = {
  minDownloadMbps: 1,
  maxPingMs: 300,
  downloadPayloadMb: 5,
  uploadPayloadBytes: 1024 * 1024,
}

export type CheckStatus = 'idle' | 'checking' | 'passed' | 'failed'

export interface NetworkResult {
  pingMs: number | null
  downloadMbps: number | null
  uploadMbps: number | null
}

interface SystemCheckProps {
  onDone: (passed: boolean) => void
  onCancel: () => void
}

export async function measurePing(): Promise<number> {
  const samples: number[] = []
  for (let i = 0; i < 3; i++) {
    const start = performance.now()
    await api.systemCheck.ping()
    samples.push(performance.now() - start)
  }
  return Math.round(samples.reduce((a, b) => a + b, 0) / samples.length)
}

export async function measureDownload(sizeMb: number): Promise<number> {
  const start = performance.now()
  const response = await api.systemCheck.download(sizeMb)
  const elapsedSeconds = (performance.now() - start) / 1000
  const bytes = response.data.byteLength || 0
  const mbps = (bytes * 8) / (elapsedSeconds * 1e6)
  return Math.round(mbps * 10) / 10
}

export async function measureUpload(payloadBytes: number): Promise<number> {
  const payload = new Blob([new Uint8Array(payloadBytes)])
  const start = performance.now()
  const response = await api.systemCheck.upload(payload)
  const elapsedSeconds = (performance.now() - start) / 1000
  const bytes = response.data.received_bytes || payloadBytes
  const mbps = (bytes * 8) / (elapsedSeconds * 1e6)
  return Math.round(mbps * 10) / 10
}

export async function measureMicrophoneLevel(stream: MediaStream, sampleMs = 1500): Promise<number> {
  const audioContext = new AudioContext()
  const analyser = audioContext.createAnalyser()
  analyser.fftSize = 512
  const source = audioContext.createMediaStreamSource(stream)
  source.connect(analyser)

  const data = new Uint8Array(analyser.frequencyBinCount)
  let peak = 0
  const sampleCount = Math.ceil((sampleMs / 1000) * 60)
  for (let i = 0; i < sampleCount; i++) {
    analyser.getByteFrequencyData(data)
    const avg = data.reduce((a, b) => a + b, 0) / data.length
    peak = Math.max(peak, avg)
    await new Promise((resolve) => setTimeout(resolve, 16))
  }

  await audioContext.close()
  return Math.min(100, Math.round(peak))
}

const SystemCheck: React.FC<SystemCheckProps> = ({ onDone, onCancel }) => {
  const { t } = useTranslation()
  const webcamRef = useRef<Webcam>(null)

  const [cameraStatus, setCameraStatus] = useState<CheckStatus>('idle')
  const [micStatus, setMicStatus] = useState<CheckStatus>('idle')
  const [networkStatus, setNetworkStatus] = useState<CheckStatus>('idle')
  const [micLevel, setMicLevel] = useState(0)
  const [networkResult, setNetworkResult] = useState<NetworkResult>({ pingMs: null, downloadMbps: null, uploadMbps: null })
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [finished, setFinished] = useState(false)

  const stopCamera = () => {
    const stream = webcamRef.current?.stream
    stream?.getTracks().forEach((track) => track.stop())
  }

  const runChecks = async () => {
    setError('')
    setRunning(true)
    setFinished(false)
    setMicLevel(0)
    setNetworkResult({ pingMs: null, downloadMbps: null, uploadMbps: null })
    setCameraStatus('checking')
    setMicStatus('checking')
    setNetworkStatus('checking')

    let cameraOk = false
    let micOk = false
    let networkOk = false

    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error(t('systemCheck.noMedia'))
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true })
        cameraOk = true
        setCameraStatus('passed')
        if (webcamRef.current) {
          webcamRef.current.stream = stream
        }
      } catch (err: any) {
        cameraOk = false
        setCameraStatus('failed')
        stopCamera()
      }

      let micStream: MediaStream | null = null
      try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const level = await measureMicrophoneLevel(micStream)
        setMicLevel(level)
        micOk = level > 0
        setMicStatus(micOk ? 'passed' : 'failed')
      } catch (err: any) {
        micOk = false
        setMicStatus('failed')
      } finally {
        micStream?.getTracks().forEach((track) => track.stop())
      }

      try {
        const [pingMs, downloadMbps, uploadMbps] = await Promise.all([
          measurePing(),
          measureDownload(NETWORK_THRESHOLDS.downloadPayloadMb),
          measureUpload(NETWORK_THRESHOLDS.uploadPayloadBytes),
        ])
        setNetworkResult({ pingMs, downloadMbps, uploadMbps })
        networkOk =
          downloadMbps >= NETWORK_THRESHOLDS.minDownloadMbps &&
          pingMs <= NETWORK_THRESHOLDS.maxPingMs
        setNetworkStatus(networkOk ? 'passed' : 'failed')
      } catch (err: any) {
        networkOk = false
        setNetworkStatus('failed')
      }
    } catch (err: any) {
      setError(err.message || t('systemCheck.failedTitle'))
      setCameraStatus('failed')
      setMicStatus('failed')
      setNetworkStatus('failed')
    } finally {
      setRunning(false)
      const passed = cameraOk && micOk && networkOk
      setFinished(true)
      onDone(passed)
    }
  }

  useEffect(() => {
    runChecks()
    return () => stopCamera()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const statusBadge = (status: CheckStatus) => {
    if (status === 'passed') return <span className="text-success fw-semibold"><FiCheck className="me-1" />{t('systemCheck.passed')}</span>
    if (status === 'failed') return <span className="text-danger fw-semibold"><FiX className="me-1" />{t('systemCheck.failed')}</span>
    if (status === 'checking') return <span className="text-secondary fw-semibold"><Spinner size="sm" className="me-1" />{t('systemCheck.checking')}</span>
    return <span className="text-muted">{t('systemCheck.idle')}</span>
  }

  const downloadBadge = networkResult.downloadMbps != null ? `${networkResult.downloadMbps} Mbps` : '-'
  const uploadBadge = networkResult.uploadMbps != null ? `${networkResult.uploadMbps} Mbps` : '-'
  const pingBadge = networkResult.pingMs != null ? `${networkResult.pingMs} ms` : '-'

  return (
    <Container className="mt-4">
      <Card className="max-w-3xl mx-auto">
        <Card.Body>
          <h1 className="mb-1">{t('systemCheck.title')}</h1>
          <p className="text-muted mb-4">{t('systemCheck.subtitle')}</p>
          {error && <Alert variant="danger">{error}</Alert>}

          <Row className="g-3 mb-3">
            <Col md={4}>
              <Card className="h-100">
                <Card.Body>
                  <h6 className="d-flex align-items-center gap-2">
                    <FiCamera /> {t('systemCheck.camera')}
                  </h6>
                  <Webcam
                    ref={webcamRef}
                    audio={false}
                    videoConstraints={{ facingMode: 'user' }}
                    style={{ width: '100%', borderRadius: 8 }}
                    mirrored
                  />
                  <div className="mt-2">{statusBadge(cameraStatus)}</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={4}>
              <Card className="h-100">
                <Card.Body>
                  <h6 className="d-flex align-items-center gap-2">
                    <FiMic /> {t('systemCheck.microphone')}
                  </h6>
                  <div className="text-center py-4">
                    <FiMic size={48} className={micStatus === 'failed' ? 'text-danger' : micStatus === 'passed' ? 'text-success' : 'text-muted'} />
                    <div className="mt-3">
                      <div className="d-flex justify-content-between small text-muted mb-1">
                        <span>{t('systemCheck.micLevel')}</span>
                        <span>{micStatus === 'checking' || micStatus === 'passed' ? `${micLevel}%` : '-'}</span>
                      </div>
                      <div className="progress" style={{ height: 10 }}>
                        <div className="progress-bar" style={{ width: `${micLevel}%`, transition: 'width 120ms linear' }} />
                      </div>
                    </div>
                  </div>
                  <div className="mt-2">{statusBadge(micStatus)}</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={4}>
              <Card className="h-100">
                <Card.Body>
                  <h6 className="d-flex align-items-center gap-2">
                    <FiWifi /> {t('systemCheck.network')}
                  </h6>
                  <dl className="mb-0">
                    <Row>
                      <Col xs={6}><dt className="small text-muted">{t('systemCheck.download')}</dt></Col>
                      <Col xs={6}><dd className="mb-1 text-end">{downloadBadge}</dd></Col>
                      <Col xs={6}><dt className="small text-muted">{t('systemCheck.upload')}</dt></Col>
                      <Col xs={6}><dd className="mb-1 text-end">{uploadBadge}</dd></Col>
                      <Col xs={6}><dt className="small text-muted">{t('systemCheck.ping')}</dt></Col>
                      <Col xs={6}><dd className="mb-0 text-end">{pingBadge}</dd></Col>
                    </Row>
                  </dl>
                  <div className="mt-2">{statusBadge(networkStatus)}</div>
                </Card.Body>
              </Card>
            </Col>
          </Row>

          <div className="d-flex flex-wrap gap-2 justify-content-between align-items-center">
            <Button variant="outline-primary" onClick={runChecks} disabled={running}>
              <FiRefreshCw className="me-2" />
              {running ? t('systemCheck.running') : t('systemCheck.runAgain')}
            </Button>
            <div className="d-flex gap-2">
              <Button variant="secondary" onClick={onCancel} disabled={running}>
                {t('common.back')}
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  onDone(cameraStatus === 'passed' && micStatus === 'passed' && networkStatus === 'passed')
                  onCancel()
                }}
                disabled={running || !finished}
              >
                {t('systemCheck.continue')} <FiArrowRight className="ms-2" />
              </Button>
            </div>
          </div>
        </Card.Body>
      </Card>
    </Container>
  )
}

export default SystemCheck