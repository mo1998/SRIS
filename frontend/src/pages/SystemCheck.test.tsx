import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SystemCheck, {
  measurePing,
  measureDownload,
  measureUpload,
  NETWORK_THRESHOLDS,
} from './SystemCheck'

const apiMock = vi.hoisted(() => ({
  systemCheck: {
    ping: vi.fn(),
    download: vi.fn(),
    upload: vi.fn(),
  },
}))

vi.mock('../services/api', () => ({ api: apiMock }))

vi.mock('react-webcam', () => ({
  default: () => <div data-testid="webcam" />,
}))

class MockAudioContext {
  analyser: any
  constructor() {
    this.analyser = {}
  }
  createAnalyser() {
    this.analyser = {
      frequencyBinCount: 256,
      getByteFrequencyData: (data: Uint8Array) => data.fill(50),
    }
    return this.analyser
  }
  createMediaStreamSource() {
    return { connect: () => {} }
  }
  close() {
    return Promise.resolve()
  }
}

const streamMock = () => ({ getTracks: () => [{ stop: vi.fn() }] })

describe('SystemCheck', () => {
  beforeEach(() => {
    apiMock.systemCheck.ping.mockReset()
    apiMock.systemCheck.download.mockReset()
    apiMock.systemCheck.upload.mockReset()
    ;(globalThis as any).AudioContext = MockAudioContext
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockResolvedValue(streamMock()),
      },
    })
  })

  it('reports a passing system check when camera, mic, and network all pass', async () => {
    apiMock.systemCheck.ping.mockResolvedValue({ data: { timestamp: Date.now() } })
    apiMock.systemCheck.download.mockResolvedValue({ data: { byteLength: 5 * 1024 * 1024 } })
    apiMock.systemCheck.upload.mockResolvedValue({ data: { received_bytes: NETWORK_THRESHOLDS.uploadPayloadBytes } })

    const onDone = vi.fn()
    render(<SystemCheck onDone={onDone} onCancel={() => {}} />)

    expect(await screen.findByText(/pre-interview system check/i)).toBeInTheDocument()
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(true), { timeout: 5000 })
    expect(screen.getAllByText('Passed').length).toBeGreaterThanOrEqual(3)
    expect(screen.getAllByText(/Mbps/i).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText(/ms/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /continue/i })).toBeEnabled()
  })

  it('reports a failing system check when media access is denied', async () => {
    ;(navigator.mediaDevices as any).getUserMedia.mockRejectedValue(new Error('Permission denied'))

    const onDone = vi.fn()
    render(<SystemCheck onDone={onDone} onCancel={() => {}} />)

    expect(await screen.findAllByText('Failed')).toBeTruthy()
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(false), { timeout: 5000 })
  })

  it('reports a failing network check when the download request fails', async () => {
    apiMock.systemCheck.ping.mockResolvedValue({ data: { timestamp: Date.now() } })
    apiMock.systemCheck.download.mockRejectedValue(new Error('slow connection'))
    apiMock.systemCheck.upload.mockResolvedValue({ data: { received_bytes: NETWORK_THRESHOLDS.uploadPayloadBytes } })

    const onDone = vi.fn()
    render(<SystemCheck onDone={onDone} onCancel={() => {}} />)

    await waitFor(() => expect(onDone).toHaveBeenCalledWith(false), { timeout: 5000 })
  })

  it('re-runs checks and updates results when clicking run again', async () => {
    apiMock.systemCheck.ping.mockResolvedValue({ data: { timestamp: Date.now() } })
    apiMock.systemCheck.download.mockResolvedValue({ data: { byteLength: 5 * 1024 * 1024 } })
    apiMock.systemCheck.upload.mockResolvedValue({ data: { received_bytes: NETWORK_THRESHOLDS.uploadPayloadBytes } })

    render(<SystemCheck onDone={() => {}} onCancel={() => {}} />)
    await screen.findByRole('button', { name: /run checks again/i }, { timeout: 5000 })
    await userEvent.click(screen.getByRole('button', { name: /run checks again/i }))
    await waitFor(() => expect(apiMock.systemCheck.ping).toHaveBeenCalledTimes(6), { timeout: 5000 })
  })
})

describe('measurement helpers', () => {
  beforeEach(() => {
    apiMock.systemCheck.ping.mockReset()
    apiMock.systemCheck.download.mockReset()
    apiMock.systemCheck.upload.mockReset()
  })

  it('measurePing returns the average latency', async () => {
    apiMock.systemCheck.ping.mockResolvedValue({ data: { timestamp: Date.now() } })
    const ms = await measurePing()
    expect(apiMock.systemCheck.ping).toHaveBeenCalledTimes(3)
    expect(typeof ms).toBe('number')
  })

  it('measureDownload converts bytes to Mbps', async () => {
    apiMock.systemCheck.download.mockResolvedValue({ data: { byteLength: 5 * 1024 * 1024 } })
    const mbps = await measureDownload(5)
    expect(apiMock.systemCheck.download).toHaveBeenCalledWith(5)
    expect(typeof mbps).toBe('number')
  })

  it('measureUpload reports throughput', async () => {
    apiMock.systemCheck.upload.mockResolvedValue({ data: { received_bytes: NETWORK_THRESHOLDS.uploadPayloadBytes } })
    const mbps = await measureUpload(NETWORK_THRESHOLDS.uploadPayloadBytes)
    expect(apiMock.systemCheck.upload).toHaveBeenCalledTimes(1)
    expect(typeof mbps).toBe('number')
  })
})