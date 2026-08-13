import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PracticeMode from './PracticeMode'

vi.mock('react-webcam', () => ({
  default: () => <div data-testid="webcam" />,
}))

const streamMock = () => ({
  getTracks: () => [{ stop: vi.fn() }],
})

class MockMediaRecorder {
  static isTypeSupported = () => true
  state = 'inactive'
  ondataavailable: any
  onstop: any
  start() {
    this.state = 'recording'
  }
  stop() {
    this.state = 'inactive'
    if (this.ondataavailable) {
      this.ondataavailable({ data: new Blob(['chunk'], { type: 'video/webm' }) })
    }
    if (this.onstop) {
      this.onstop()
    }
  }
}

describe('PracticeMode', () => {
  beforeEach(() => {
    ;(globalThis as any).MediaRecorder = MockMediaRecorder
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue(streamMock()) },
    })
    vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock')
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('shows the sample question and starts a recording', async () => {
    render(<PracticeMode onExit={() => {}} />)

    expect(screen.getByRole('heading', { name: /sample question/i })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /start recording/i }))

    expect(await screen.findByRole('button', { name: /stop recording/i })).toBeInTheDocument()
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({ audio: true, video: true })
  })

  it('previews the recording after stopping and allows trying again', async () => {
    render(<PracticeMode onExit={() => {}} />)

    await userEvent.click(screen.getByRole('button', { name: /start recording/i }))
    await userEvent.click(await screen.findByRole('button', { name: /stop recording/i }))

    expect(await screen.findByRole('button', { name: /try again/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /i'm ready/i })).toBeInTheDocument()
    expect(screen.getByText(/practice recordings are never stored/i)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(screen.getByRole('button', { name: /start recording/i })).toBeInTheDocument()
  })

  it('auto-stops recording when the two-minute window elapses', async () => {
    vi.useFakeTimers()
    render(<PracticeMode onExit={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /start recording/i }))
    await vi.advanceTimersByTimeAsync(0)
    expect(screen.getByRole('button', { name: /stop recording/i })).toBeInTheDocument()

    await vi.advanceTimersByTimeAsync(121 * 1000)
    expect(screen.queryByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('notifies on exit and revokes preview object URLs', async () => {
    const onExit = vi.fn()
    render(<PracticeMode onExit={onExit} />)

    await userEvent.click(screen.getByRole('button', { name: /start recording/i }))
    await userEvent.click(await screen.findByRole('button', { name: /stop recording/i }))
    await userEvent.click(await screen.findByRole('button', { name: /i'm ready/i }))

    expect(onExit).toHaveBeenCalled()
  })
})